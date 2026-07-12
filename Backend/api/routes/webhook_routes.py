from __future__ import annotations

import logging
import json
from typing import Any, Dict, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import Response

from config import get_config
from services.stt.language_detector import LanguageDetector
from services.stt.whisper_service import WhisperService
from services.telephony.twilio_client import TwilioClient
from services.telephony.call_manager import CallManager
from services.database.supabase_client import get_db_client
from services.database.repository import Repository
from services.scoring.scoring_engine import ScoringEngine
from services.database.models import LeadStatus
from services.llm.kb_context_injection import KBContextInjectionService
from services.call_recording_service import CallRecordingService
from worker.queue_manager import QueueManager, JobType


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhook/twilio", tags=["Twilio Webhooks"])

# Simple in-memory cache to hold generated audio for Twilio to fetch via TwiML <Play>
# In production, use Redis or S3 for multi-worker scaling
audio_cache: dict[str, bytes] = {}

# Cache for call sessions: {call_sid -> {session_id, lead_id, conversation_history, turn_count}}
call_sessions: dict[str, dict] = {}

def _xml_response(xml: str) -> Response:
        if not xml.strip().startswith("<?xml"):
                xml = f'<?xml version="1.0" encoding="UTF-8"?>\n{xml}'
        return Response(content=xml, media_type="application/xml")


def _form_value(form: Dict[str, Any], key: str, default: Optional[str] = None) -> Optional[str]:
        value = form.get(key, default)
        return str(value) if value is not None else None


async def _initialize_call_session(call_sid: str, db_client, repository) -> Optional[Dict]:
        """
        Initialize or retrieve call session information from database.
        """
        try:
                # Try to find existing session in cache
                if call_sid in call_sessions:
                        return call_sessions[call_sid]
                
                # If not in cache, we need to link it to a lead
                # This will be set when call_initiator creates the session
                logger.warning(f"Call session {call_sid} not found in cache - will be linked later")
                return None
        except Exception as e:
                logger.error(f"Error initializing call session: {e}")
                return None


async def _save_conversation_turn(
        session_id: UUID,
        call_sid: str,
        user_text: str,
        ai_response: str,
        detected_lang: str,
        repository: Repository
):
        """Save conversation turn to call session."""
        try:
                # Get current session
                session = await repository.get_call_session(session_id)
                if not session:
                        logger.warning(f"Session {session_id} not found")
                        return
                
                # Parse existing history
                conversation_history = json.loads(session.get("conversation_history") or "[]")
                
                # Add new turn
                turn = {
                        "user": user_text,
                        "ai": ai_response,
                        "language": detected_lang,
                        "timestamp": str(datetime.utcnow())
                }
                conversation_history.append(turn)
                
                # Update session
                await repository.update_call_session(
                        session_id=session_id,
                        conversation_history=conversation_history
                )
                
                logger.debug(f"Saved turn #{len(conversation_history)} for session {session_id}")
        
        except Exception as e:
                logger.error(f"Error saving conversation turn: {e}")


async def _score_and_assign_lead(
        lead_id: UUID,
        session_id: UUID,
        repository: Repository,
        scoring_engine: ScoringEngine,
        queue_manager: QueueManager,
        user_engagement: int = 70,
        user_interest: int = 70,
        user_sentiment: int = 70,
        classification_override: Optional[str] = None
):
        """
        Score lead based on conversation and auto-assign/follow-up.
        
        Args:
                lead_id: Lead ID
                session_id: Call session ID
                user_engagement: Engagement score (0-100)
                user_interest: Interest score (0-100)
                user_sentiment: Sentiment score (0-100)
        """
        try:
                # Normalize scores to 0-1
                engagement = user_engagement / 100.0
                interest = user_interest / 100.0
                sentiment = user_sentiment / 100.0
                
                # Calculate composite score
                composite = (interest + engagement + sentiment) / 3.0
                
                # Classify
                if classification_override and classification_override in ["HOT", "WARM", "COLD"]:
                        classification = classification_override
                else:
                        if composite >= 0.75:
                                classification = "HOT"
                        elif composite >= 0.50:
                                classification = "WARM"
                        else:
                                classification = "COLD"
                
                logger.info(f"Lead scoring: composite={composite:.2f} ({classification})")
                
                # Create score record
                score_record = await repository.create_lead_score(
                        lead_id=lead_id,
                        call_session_id=session_id,
                        interest_score=interest,
                        engagement_score=engagement,
                        sentiment_score=sentiment,
                        classification=classification
                )
                
                logger.info(f"✅ Created lead score: {score_record['id']}")
                
                # Update lead status
                await repository.update_lead(
                        lead_id=lead_id,
                        status=LeadStatus.INTERESTED.value if classification in ("HOT", "WARM") else LeadStatus.NEW.value
                )
                
                # Auto-actions based on classification
                if classification == "HOT":
                        # Assign to RM immediately
                        rm_name = get_config().default_rm_name or "Auto"
                        await repository.assign_lead_to_rm(lead_id, rm_name)
                        logger.info(f"[SCORE] HOT lead assigned to RM: {rm_name}")
                
                elif classification == "WARM":
                        # Schedule WhatsApp follow-up
                        lead = await repository.get_lead(lead_id)
                        lead_lang = lead.get("language", "hi") if lead else "hi"
                        job = {
                                "lead_id": str(lead_id),
                                "phone": lead.get("phone") if lead else None,
                                "message_type": "warm_follow_up",
                                "language": lead_lang,
                                "message": "Thanks for chatting with us! We'll be in touch soon."
                        }
                        await queue_manager.enqueue_job(JobType.SEND_WHATSAPP.value, job)
                        logger.info(f"[SCORE] Scheduled WhatsApp follow-up for WARM lead in language '{lead_lang}'")
        
        except Exception as e:
                logger.error(f"Error scoring lead: {e}")


@router.api_route("/voice", methods=["GET", "POST"])
async def voice_webhook(request: Request) -> Response:
        """Initial Twilio Voice webhook for inbound calls."""

        form = await request.form() if request.method == "POST" else {}
        caller = _form_value(dict(form), "From", "unknown")
        call_sid = _form_value(dict(form), "CallSid", "unknown")
        
        session_id = request.query_params.get("session_id")
        lead_id = request.query_params.get("lead_id")
        
        logger.info(f"Inbound voice webhook received from {caller} (CallSid: {call_sid})")

        # Initialize call session in cache
        if call_sid not in call_sessions:
                call_sessions[call_sid] = {
                        "call_sid": call_sid,
                        "from_number": caller,
                        "session_id": session_id,
                        "lead_id": lead_id,
                        "turn_count": 0,
                        "started_at": str(datetime.utcnow())
                }
                logger.info(f"Created call session cache for {call_sid}")

        client = TwilioClient()
        
        callback_path = "/api/webhook/twilio/recording"
        if session_id and lead_id:
                callback_path += f"?session_id={session_id}&lead_id={lead_id}"
                
        twiml = client.build_voice_entry_twiml(
                greeting_text="Hello, welcome to Sambhaash AI. Please speak after the beep.",
                recording_callback_path=callback_path,
        )
        return Response(content=twiml, media_type="application/xml")


@router.post("/recording")
async def recording_webhook(request: Request) -> Response:
        """Receive a Twilio recording, transcribe it, classify language, hit LLM, generate TTS, and reply."""

        settings = get_config()
        form = await request.form()
        form_data = dict(form)

        recording_url = _form_value(form_data, "RecordingUrl")
        call_sid = _form_value(form_data, "CallSid", "")
        from_number = _form_value(form_data, "From", "")
        duration = _form_value(form_data, "RecordingDuration", "0")

        client = TwilioClient()
        manager = CallManager()

        if not recording_url:
                logger.warning("Recording webhook called without RecordingUrl (CallSid=%s)", call_sid)
                return Response(
                        content=client.build_say_twiml("We did not receive any audio. Please try again."),
                        media_type="application/xml",
                )

        if not client.configured:
                logger.error("Twilio credentials are not configured in backend/env")
                return Response(
                        content=client.build_say_twiml("We are having trouble connecting right now. Please call again later."),
                        media_type="application/xml",
                )

        session_id = request.query_params.get("session_id")
        lead_id = request.query_params.get("lead_id")

        if call_sid not in call_sessions:
            call_sessions[call_sid] = {
                "call_sid": call_sid,
                "from_number": from_number,
                "session_id": session_id,
                "lead_id": lead_id,
                "turn_count": 0,
                "started_at": str(datetime.utcnow())
            }
            logger.info(f"Created late call session cache for {call_sid}")

        db_client = None
        repository = None
        
        try:
                # Initialize database access
                db_client = await get_db_client()
                repository = Repository(db_client)
                scoring_engine = ScoringEngine(repository)
                queue_manager = QueueManager()
                
                # Get call session info
                session_info = call_sessions.get(call_sid, {})
                if not session_info.get("session_id"):
                        logger.info(f"No session found for inbound call {call_sid}, creating new lead and session on the fly.")
                        try:
                                lead = await repository.create_lead(
                                        phone=from_number or "unknown",
                                        source="inbound_call",
                                )
                                new_session = await repository.create_call_session(
                                        lead_id=lead["id"],
                                        language_detected="english"
                                )
                                session_info["session_id"] = str(new_session["id"])
                                session_info["lead_id"] = str(lead["id"])
                                call_sessions[call_sid] = session_info
                        except Exception as e:
                                logger.error(f"Failed to create inbound session: {e}")
                                return Response(
                                        content=client.build_say_twiml("Sorry, we lost the call session. Please call again."),
                                        media_type="application/xml",
                                )
                
                session_id = session_info.get("session_id")
                lead_id = session_info.get("lead_id")
                turn_count = session_info.get("turn_count", 0) + 1
                
                logger.info(f"Processing recording for call {call_sid}, turn {turn_count}")
                
                # 1. STT
                stt = WhisperService()
                language_detector = LanguageDetector()
                
                transcript = stt.transcribe_recording_url(
                        recording_url=recording_url,
                        twilio_account_sid=settings.twilio_account_sid or "",
                        twilio_auth_token=settings.twilio_auth_token or "",
                )
                detected_lang = language_detector.detect_language(transcript)
                
                logger.info(f"User said: {transcript} (Lang: {detected_lang})")

                # 1.5 Retrieve KB Context
                kb_context = None
                try:
                        if session_id and lead_id:
                                kb_service = KBContextInjectionService(db_client=db_client)
                                kb_context = await kb_service.retrieve_context_for_call(
                                        call_session_id=UUID(session_id),
                                        lead_id=UUID(lead_id),
                                        user_text=transcript,
                                        language=detected_lang,
                                        top_k=3,
                                        min_score=0.3
                                )
                                logger.info(f"[KB] Retrieved {len(kb_context.get('context_blocks', []))} KB chunks")
                except Exception as e:
                        logger.error(f"[KB] Failed to retrieve context: {e}")
                        kb_context = None

                # 2. LangGraph Orchestration
                from orchestration.graph import app
                from langchain_core.messages import HumanMessage
                
                logger.info(f"Invoking LangGraph for session {session_id}")
                
                # Extract the pre-formatted string from the KB retrieval dict
                kb_text = kb_context.get("formatted_context", "") if kb_context else ""
                
                input_state = {
                    "messages": [HumanMessage(content=transcript)],
                    "session_id": session_id,
                    "lead_id": lead_id,
                    "lead_language": detected_lang,
                    "kb_context": kb_text
                }
                
                # The thread_id tells the Supabase checkpointer which row to update
                config = {"configurable": {"thread_id": session_id}}
                
                # Run the state machine
                final_state = await app.ainvoke(input_state, config=config)
                
                # Extract the AI's final response and outcome
                ai_message = final_state["messages"][-1].content if final_state.get("messages") else "I'm sorry, I encountered an error."
                outcome = final_state.get("outcome", "UNKNOWN")
                
                reply_text = ai_message
                target_lang = detected_lang
                is_ending = outcome in ["HOT", "COLD"]
                
                logger.info(f"LangGraph response: {reply_text} (Target Lang: {target_lang}, Outcome: {outcome})")

                # 3. Save conversation turn to database (in background so we don't delay TTS)
                import asyncio
                asyncio.create_task(_save_conversation_turn(
                        session_id=session_id,
                        call_sid=call_sid,
                        user_text=transcript,
                        ai_response=reply_text,
                        detected_lang=detected_lang,
                        repository=repository
                ))

                # 4. TTS Generation
                audio_bytes = await manager.generate_tts(text=reply_text, language=target_lang)
                
                # 5. Cache audio bytes for Twilio <Play> fetch
                audio_cache[call_sid] = audio_bytes

                # 6. Check if max turns reached or LLM decided to end call
                max_turns = settings.max_turns_per_session
                if turn_count >= max_turns or is_ending:
                        logger.info(f"Call ending. Max turns reached: {turn_count >= max_turns}, LLM ending: {is_ending} for call {call_sid}")
                        
                        # Score and assign lead
                        await _score_and_assign_lead(
                                lead_id=UUID(lead_id),
                                session_id=UUID(session_id),
                                repository=repository,
                                scoring_engine=scoring_engine,
                                queue_manager=queue_manager,
                                classification_override=outcome
                        )
                        
                        # 6.1 Save call recording (Phase 2B) - Background Queue
                        try:
                                await queue_manager.enqueue_job(
                                        "process_recording",
                                        payload={
                                                "call_session_id": session_id,
                                                "recording_url": recording_url,
                                                "twilio_recording_sid": call_sid,
                                                "twilio_call_sid": call_sid,
                                                "duration_seconds": int(duration) if duration else 0
                                        },
                                        priority=1
                                )
                                logger.info(f"[RECORDING] Enqueued recording job for session {session_id}")
                        except Exception as e:
                                logger.error(f"[RECORDING] Failed to enqueue recording job: {e}")
                        
                        # End call with summary or LLM's final response
                        final_reply = reply_text if is_ending else "Thanks for chatting with us! Our team will be in touch shortly. Goodbye!"
                        audio_bytes = await manager.generate_tts(text=final_reply, language=target_lang)
                        audio_cache[call_sid] = audio_bytes
                        audio_url = client.build_base_url(f"/api/webhook/twilio/audio/{call_sid}")
                        
                        # Cleanup
                        del call_sessions[call_sid]
                        
                        return _xml_response(f'<Response><Play>{audio_url}</Play><Hangup/></Response>')
                
                # 7. Build returning TwiML with next recording
                audio_url = client.build_base_url(f"/api/webhook/twilio/audio/{call_sid}")
                record_url = client.build_base_url("/api/webhook/twilio/recording")
                
                # Update turn count
                call_sessions[call_sid]["turn_count"] = turn_count
                
                twiml = f'''<Response>
                    <Play>{audio_url}</Play>
                    <Record action="{record_url}" method="POST" playBeep="true" maxLength="60" trim="trim-silence" />
                </Response>'''
                
                return _xml_response(twiml)

        except Exception as exc:  # pragma: no cover
                logger.exception("Failed to process full Twilio conversational turn: %s", exc)
                return Response(
                        content=client.build_say_twiml("Sorry, I could not process your input just now. Please speak again."),
                        media_type="application/xml",
                )

@router.get("/audio/{call_sid}")
async def fetch_audio(call_sid: str) -> Response:
        """Endpoint for Twilio <Play> to fetch the generated audio bytes."""
        audio_data = audio_cache.get(call_sid)
        if not audio_data:
            logger.error(f"No audio found in cache for CallSid: {call_sid}")
            # Return an empty response so it skips silently instead of failing the call
            return Response(content=b"", media_type="audio/wav")
        
        return Response(content=audio_data, media_type="audio/wav")

@router.post("/whatsapp")
async def whatsapp_webhook(request: Request) -> Response:
        """Optional Twilio WhatsApp sandbox webhook."""

        form = await request.form()
        message = _form_value(dict(form), "Body", "") or ""
        from_number = _form_value(dict(form), "From", "unknown")
        logger.info("WhatsApp message received from %s", from_number)

        client = TwilioClient()
        reply = client.build_whatsapp_reply_twiml(
                "Thanks for reaching out! A Relationship Manager will be in touch shortly."
        )
        return Response(content=reply, media_type="application/xml")

@router.post("/status")
async def status_webhook(
        request: Request,
        session_id: Optional[str] = None,
        lead_id: Optional[str] = None
) -> Response:
        """Status callback from Twilio to handle failed/no-answer calls."""
        form = await request.form()
        form_data = dict(form)
        
        call_sid = _form_value(form_data, "CallSid", "")
        call_status = _form_value(form_data, "CallStatus", "").lower()
        answered_by = _form_value(form_data, "AnsweredBy", "").lower()
        
        logger.info(f"[TWILIO STATUS] CallSid: {call_sid}, Status: {call_status}, AnsweredBy: {answered_by}, Lead: {lead_id}")
        
        # We only care about terminal failure states or voicemail
        is_voicemail = answered_by.startswith("machine")
        is_failed = call_status in ["failed", "busy", "no-answer", "canceled"]
        
        if is_voicemail or is_failed:
                logger.warning(f"[TWILIO STATUS] Call {call_sid} failed or hit voicemail. Updating lead to FAILED...")
                if lead_id:
                        db_client = None
                        try:
                                db_client = await get_db_client()
                                repository = Repository(db_client)
                                await repository.update_lead(
                                        lead_id=UUID(lead_id),
                                        status=LeadStatus.FAILED.value
                                )
                                logger.info(f"[TWILIO STATUS] Successfully marked lead {lead_id} as FAILED")
                        except Exception as e:
                                logger.error(f"[TWILIO STATUS] Error updating lead {lead_id} status: {e}")
        elif call_status == "completed":
                # Handle abrupt hangups! If the call completed but wasn't scored, score it as WARM.
                if lead_id and session_id:
                        db_client = None
                        try:
                                db_client = await get_db_client()
                                repository = Repository(db_client)
                                lead = await repository.get_lead(UUID(lead_id))
                                
                                # If it's still 'CONTACTED', it means the user hung up before max_turns or the LLM formally ended it!
                                if lead and lead.get("status") == LeadStatus.CONTACTED.value:
                                        logger.info(f"[TWILIO STATUS] Lead {lead_id} hung up abruptly. Auto-scoring as WARM...")
                                        queue_manager = QueueManager()
                                        scoring_engine = ScoringEngine(repository)
                                        await _score_and_assign_lead(
                                                lead_id=UUID(lead_id),
                                                session_id=UUID(session_id),
                                                repository=repository,
                                                scoring_engine=scoring_engine,
                                                queue_manager=queue_manager,
                                                classification_override="WARM"
                                        )
                        except Exception as e:
                                logger.error(f"[TWILIO STATUS] Error auto-scoring on hangup: {e}")
        
        # Always return HTTP 200 to Twilio
        return Response(content="<Response></Response>", media_type="application/xml")
