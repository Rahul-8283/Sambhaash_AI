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
from worker.queue_manager import QueueManager, JobType


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhook/twilio", tags=["Twilio Webhooks"])

# Simple in-memory cache to hold generated audio for Twilio to fetch via TwiML <Play>
# In production, use Redis or S3 for multi-worker scaling
audio_cache: dict[str, bytes] = {}

# Cache for call sessions: {call_sid -> {session_id, lead_id, conversation_history, turn_count}}
call_sessions: dict[str, dict] = {}

def _xml_response(xml: str) -> Response:
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
        user_sentiment: int = 70
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
                        job = {
                                "lead_id": str(lead_id),
                                "phone": (await repository.get_lead(lead_id)).get("phone"),
                                "message": "Thanks for chatting with us! We'll be in touch soon."
                        }
                        await queue_manager.enqueue_job(JobType.SEND_WHATSAPP.value, job)
                        logger.info("[SCORE] Scheduled WhatsApp follow-up for WARM lead")
        
        except Exception as e:
                logger.error(f"Error scoring lead: {e}")


@router.api_route("/voice", methods=["GET", "POST"])
async def voice_webhook(request: Request) -> Response:
        """Initial Twilio Voice webhook for inbound calls."""

        form = await request.form() if request.method == "POST" else {}
        caller = _form_value(dict(form), "From", "unknown")
        call_sid = _form_value(dict(form), "CallSid", "unknown")
        
        logger.info(f"Inbound voice webhook received from {caller} (CallSid: {call_sid})")

        # Initialize call session in cache
        # The lead_id and session_id will be set by call_initiator when it creates the session
        if call_sid not in call_sessions:
                call_sessions[call_sid] = {
                        "call_sid": call_sid,
                        "from_number": caller,
                        "session_id": None,  # Will be set by call_initiator
                        "lead_id": None,     # Will be set by call_initiator
                        "turn_count": 0,
                        "started_at": str(datetime.utcnow())
                }
                logger.info(f"Created call session cache for {call_sid}")

        client = TwilioClient()
        twiml = client.build_voice_entry_twiml(
                greeting_text="Hello, welcome to Sambhaash AI. Please speak after the beep.",
                recording_callback_path="/api/webhook/twilio/recording",
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

        db_client = None
        repository = None
        
        try:
                # Initialize database access
                db_client = await get_db_client()
                repository = Repository(db_client)
                scoring_engine = ScoringEngine(repository)
                queue_manager = QueueManager()
                
                # Get call session info
                session_info = call_sessions.get(call_sid)
                if not session_info:
                        logger.error(f"No session info for call_sid {call_sid}")
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

                # 2. LLM Orchestration
                manager = CallManager()
                reply_text, target_lang = await manager.process_turn(
                    call_sid=call_sid,
                    user_text=transcript,
                    language=detected_lang
                )

                logger.info(f"AI response: {reply_text} (Target Lang: {target_lang})")

                # 3. Save conversation turn to database
                await _save_conversation_turn(
                        session_id=session_id,
                        call_sid=call_sid,
                        user_text=transcript,
                        ai_response=reply_text,
                        detected_lang=detected_lang,
                        repository=repository
                )

                # 4. TTS Generation
                audio_bytes = await manager.generate_tts(text=reply_text, language=target_lang)
                
                # 5. Cache audio bytes for Twilio <Play> fetch
                audio_cache[call_sid] = audio_bytes

                # 6. Check if max turns reached (auto-end call)
                max_turns = settings.max_turns_per_session
                if turn_count >= max_turns:
                        logger.info(f"Max turns ({max_turns}) reached for call {call_sid}")
                        
                        # Score and assign lead
                        await _score_and_assign_lead(
                                lead_id=UUID(lead_id),
                                session_id=UUID(session_id),
                                repository=repository,
                                scoring_engine=scoring_engine,
                                queue_manager=queue_manager
                        )
                        
                        # End call with summary
                        summary_text = "Thanks for chatting with us! Our team will be in touch shortly. Goodbye!"
                        audio_bytes = await manager.generate_tts(text=summary_text, language=target_lang)
                        audio_cache[call_sid] = audio_bytes
                        audio_url = client.build_base_url(f"/api/webhook/twilio/audio/{call_sid}")
                        
                        # Cleanup
                        del call_sessions[call_sid]
                        
                        return _xml_response(f'<Response><Play>{audio_url}</Play></Response>')
                
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
        finally:
                # Cleanup
                if db_client:
                        try:
                                await db_client.disconnect()
                        except:
                                pass

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
                "Thanks for messaging Sambhaash AI. Your request is received and will be processed by the team."
        )
        return Response(content=reply, media_type="application/xml")
