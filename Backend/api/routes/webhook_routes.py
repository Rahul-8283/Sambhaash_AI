from __future__ import annotations

import asyncio
import logging
import json
from typing import Any, Dict, Optional
from uuid import UUID
from datetime import datetime, timezone
from xml.sax.saxutils import escape as xml_escape

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from config import get_config
from api.twilio_auth import verify_twilio_signature
from services.stt.language_detector import LanguageDetector
from services.stt.whisper_service import WhisperService
from services.telephony.twilio_client import TwilioClient
from services.telephony.call_manager import CallManager
from services.database.supabase_client import get_db_client
from services.database.repository import Repository
from services.scoring.scoring_engine import ScoringEngine
from services.database.models import LeadStatus
from orchestration.outcome import classify_outcome, is_do_not_contact, user_texts_from_history
from orchestration.history import history_to_messages as conversation_messages
from orchestration.objections import classify_objection
from utils.language import call_language, last_turn_language, to_language_code
from services.llm.kb_context_injection import KBContextInjectionService
from services.rm_allocator import RM, choose_rm
from services.call_recording_service import CallRecordingService
from worker.queue_manager import QueueManager, JobType


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhook/twilio", tags=["Twilio Webhooks"])

# Simple in-memory cache to hold generated audio for Twilio to fetch via TwiML <Play>
# In production, use Redis or S3 for multi-worker scaling
# One entry per <Play> chunk. A chunk is either finished bytes or a task still
# synthesizing; fetch_audio awaits a task, since Twilio only asks for a chunk
# when it is ready to play it.
audio_cache: dict[str, list] = {}

# Cache for call sessions: {call_sid -> {session_id, lead_id, conversation_history, turn_count}}
call_sessions: dict[str, dict] = {}

_stt_service: Optional[WhisperService] = None
_language_detector: Optional[LanguageDetector] = None
_call_manager: Optional[CallManager] = None


def _services():
        """Per-process singletons: building these clients on every turn costs time."""
        global _stt_service, _language_detector, _call_manager
        if _stt_service is None:
                _stt_service = WhisperService()
        if _language_detector is None:
                _language_detector = LanguageDetector()
        if _call_manager is None:
                _call_manager = CallManager()
        return _stt_service, _language_detector, _call_manager


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
                conversation_history = session.get("conversation_history") or []
                if isinstance(conversation_history, str):
                        conversation_history = json.loads(conversation_history)
                
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


async def _persist_language(repository, lead_id, session_id, code: str) -> None:
        """Remember the language the caller actually speaks (WhatsApp follow-up uses it)."""
        try:
                if lead_id:
                        await repository.update_lead(lead_id=UUID(lead_id), language=code)
                if session_id:
                        await repository.update_call_session(UUID(session_id), language_detected=code)
        except Exception as e:
                logger.error(f"Could not store detected language: {e}")


async def _score_and_assign_lead(
        lead_id: UUID,
        session_id: UUID,
        repository: Repository,
        scoring_engine: ScoringEngine,
        queue_manager: QueueManager,
        classification_override: Optional[str] = None
) -> Optional[RM]:
        """
        Score the lead from the stored conversation and auto-assign/follow-up.
        Returns the RM a HOT lead was assigned to (None for any other outcome),
        so the caller can offer a live transfer.

        The ScoringEngine scores the whole call (intent, engagement, sentiment).
        A clear HOT or COLD signal from the caller (``classification_override``)
        decides the classification; anything else (WARM / UNKNOWN / None) falls
        back to the engine's own classification.

        Args:
                lead_id: Lead ID
                session_id: Call session ID
                classification_override: Outcome from the keyword heuristics
        """
        assigned_rm: Optional[RM] = None
        try:
                session = await repository.get_call_session(session_id) or {}
                history = session.get("conversation_history") or []

                duration_seconds = 0
                started_at = session.get("created_at")
                if started_at:
                        if started_at.tzinfo is None:
                                started_at = started_at.replace(tzinfo=timezone.utc)
                        duration_seconds = max(0, int((datetime.now(timezone.utc) - started_at).total_seconds()))

                scored = scoring_engine.score_conversation(history, duration_seconds)
                engagement = scored["engagement_score"]
                interest = scored["intent_score"]
                sentiment = scored["sentiment_score"]
                composite = scored["composite_score"]

                do_not_contact = any(is_do_not_contact(t) for t in user_texts_from_history(history))

                if do_not_contact:
                        classification = "COLD"
                elif classification_override in ("HOT", "COLD"):
                        classification = classification_override
                else:
                        classification = scored["classification"]

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

                if duration_seconds:
                        await repository.update_call_session(session_id, duration_seconds=duration_seconds)

                if classification == "HOT":
                        # The caller came round: their objections were handled
                        try:
                                for objection in await repository.list_objections_by_session(session_id):
                                        if not objection.get("resolved"):
                                                await repository.mark_objection_resolved(objection["id"])
                        except Exception as e:
                                logger.error(f"Could not resolve objections: {e}")
                
                # Update lead status. COLD leads must NOT go back to NEW: the call
                # initiator dials every NEW lead each poll cycle, so that would
                # re-call people who just declined, indefinitely.
                await repository.update_lead(
                        lead_id=lead_id,
                        # REJECTED is never dialled or nurtured: the caller asked not to be contacted
                        status=(
                                LeadStatus.REJECTED.value if do_not_contact
                                else LeadStatus.INTERESTED.value if classification in ("HOT", "WARM")
                                else LeadStatus.FOLLOW_UP.value
                        )
                )
                if do_not_contact:
                        logger.info(f"[SCORE] Lead {lead_id} asked not to be contacted; marked REJECTED")
                
                # Auto-actions based on classification
                if classification == "HOT":
                        # Assign to RM immediately
                        rm = await choose_rm(repository)
                        assigned_rm = rm
                        await repository.assign_lead_to_rm(lead_id, rm.name)
                        logger.info(f"[SCORE] HOT lead assigned to RM: {rm.name}")
                        if rm.phone:
                                try:
                                        lead = await repository.get_lead(lead_id) or {}
                                        await queue_manager.enqueue_job(JobType.SEND_WHATSAPP.value, {
                                                "lead_id": str(lead_id),
                                                "message_type": "rm_notification",
                                                "rm_phone": rm.phone,
                                                "message": (
                                                        f"New HOT lead assigned to you: {lead.get('name') or 'Unknown'}, "
                                                        f"{lead.get('phone') or 'no phone'} "
                                                        f"(language: {lead.get('language') or 'n/a'}). "
                                                        "Please call them back soon."
                                                ),
                                        })
                                except Exception as e:
                                        logger.error(f"[SCORE] Could not queue RM notification: {e}")
                
                elif classification == "WARM":
                        # Schedule WhatsApp follow-up
                        lead = await repository.get_lead(lead_id)
                        lead_lang = lead.get("language", "hi") if lead else "hi"
                        job = {
                                "lead_id": str(lead_id),
                                "message_type": "warm_follow_up",
                                "language": lead_lang,
                        }
                        await queue_manager.enqueue_job(JobType.SEND_WHATSAPP.value, job)
                        logger.info(f"[SCORE] Scheduled WhatsApp follow-up for WARM lead in language '{lead_lang}'")
                        
                # Always enqueue the summary generation job after scoring
                try:
                        summary_job = {
                                "session_id": str(session_id),
                                "lead_id": str(lead_id)
                        }
                        await queue_manager.enqueue_job(JobType.SEND_SUMMARY.value, summary_job)
                        logger.info(f"[SCORE] Enqueued SEND_SUMMARY for session {session_id}")
                except Exception as e:
                        logger.error(f"[SCORE] Failed to enqueue SEND_SUMMARY: {e}")
        
        except Exception as e:
                logger.error(f"Error scoring lead: {e}")
        return assigned_rm


@router.api_route("/voice", methods=["GET", "POST"], dependencies=[Depends(verify_twilio_signature)])
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


@router.post("/recording", dependencies=[Depends(verify_twilio_signature)])
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
        _, _, manager = _services()

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
                
                # The stored turns give the language already established on this call,
                # which hints Whisper and stabilises very short replies
                call_session = await repository.get_call_session(UUID(session_id)) if session_id else None
                stored_history = (call_session or {}).get("conversation_history") or []
                previous_lang = last_turn_language(stored_history)

                # 1. STT
                stt, language_detector, _ = _services()
                
                # Blocking download + transcription: run off the event loop
                transcript = await asyncio.to_thread(
                        stt.transcribe_recording_url,
                        recording_url=recording_url,
                        twilio_account_sid=settings.twilio_account_sid or "",
                        twilio_auth_token=settings.twilio_auth_token or "",
                        language=previous_lang,
                )
                detected_lang, lang_confident = call_language(
                        language_detector.detect_language(transcript), transcript, previous_lang
                )
                
                logger.info(f"User said: {transcript} (Lang: {detected_lang}, hint: {previous_lang})")
                
                print(f"\n{'='*60}")
                print(f"🗣️  USER SAID: {transcript}")
                print(f"{'='*60}\n")

                # 1.5 KB retrieval and the stored history are independent: fetch together
                async def _retrieve_kb():
                        if not (session_id and lead_id):
                                return None
                        try:
                                kb_service = KBContextInjectionService(db_client=db_client)
                                ctx = await kb_service.retrieve_context_for_call(
                                        call_session_id=UUID(session_id),
                                        lead_id=UUID(lead_id),
                                        user_text=transcript,
                                        language=detected_lang,
                                        top_k=3,
                                        min_score=0.3
                                )
                                logger.info(f"[KB] Retrieved {len(ctx.get('context_blocks', []))} KB chunks")
                                return ctx
                        except Exception as e:
                                logger.error(f"[KB] Failed to retrieve context: {e}")
                                return None

                kb_context = await _retrieve_kb()
                history = conversation_messages(stored_history)

                # 2. LangGraph Orchestration
                from orchestration.graph import app
                from langchain_core.messages import HumanMessage

                logger.info(f"Invoking LangGraph for session {session_id}")

                # Extract the pre-formatted string from the KB retrieval dict
                kb_text = kb_context.get("formatted_context", "") if kb_context else ""

                input_state = {
                    "messages": history + [HumanMessage(content=transcript)],
                    "session_id": session_id,
                    "lead_id": lead_id,
                    "lead_language": detected_lang,
                    "kb_context": kb_text
                }

                # Run the state machine (memory comes from the stored turns above)
                final_state = await app.ainvoke(input_state)
                
                # Extract the AI's final response and outcome
                ai_message = final_state["messages"][-1].content if final_state.get("messages") else "I'm sorry, I encountered an error."
                outcome = final_state.get("outcome", "UNKNOWN")

                # The objection path ran: record what the caller objected to
                objections_raised = final_state.get("detected_objections") or []
                if objections_raised and session_id:
                        objection_text = str(objections_raised[-1])
                        try:
                                await repository.create_objection(
                                        call_session_id=UUID(session_id),
                                        objection_type=classify_objection(objection_text),
                                        objection_text=objection_text[:500],
                                )
                        except Exception as e:
                                logger.error(f"Could not log objection: {e}")
                
                reply_text = ai_message
                target_lang = detected_lang
                is_ending = outcome in ["HOT", "COLD"]
                
                logger.info(f"LangGraph response: {reply_text} (Target Lang: {target_lang}, Outcome: {outcome})")
                
                print(f"\n{'='*60}")
                print(f"🤖  AI REPLIED: {reply_text}")
                print(f"   (Outcome: {outcome})")
                print(f"{'='*60}\n")

                # 3+4. Save the turn (the next turn reads it back) while TTS renders
                new_code = to_language_code(detected_lang)
                persist_language = (
                        lang_confident and new_code != to_language_code(previous_lang, default="")
                )
                _, tts_started, _ = await asyncio.gather(
                        _save_conversation_turn(
                                session_id=session_id,
                                call_sid=call_sid,
                                user_text=transcript,
                                ai_response=reply_text,
                                detected_lang=detected_lang,
                                repository=repository
                        ),
                        manager.start_tts(text=reply_text, language=target_lang),
                        _persist_language(repository, lead_id, session_id, new_code) if persist_language else asyncio.sleep(0),
                )

                # 5. Cache the chunks for Twilio's <Play> fetches
                first_chunk, pending_chunks = tts_started
                audio_cache[call_sid] = [first_chunk, *pending_chunks]

                # 6. Check if max turns reached or LLM decided to end call
                max_turns = settings.max_turns_per_session
                if turn_count >= max_turns or is_ending:
                        logger.info(f"Call ending. Max turns reached: {turn_count >= max_turns}, LLM ending: {is_ending} for call {call_sid}")
                        
                        # Score and assign lead
                        assigned_rm = await _score_and_assign_lead(
                                lead_id=UUID(lead_id),
                                session_id=UUID(session_id),
                                repository=repository,
                                scoring_engine=scoring_engine,
                                queue_manager=queue_manager,
                                classification_override=outcome
                        )
                        
                        # End on the LLM's own reply, which was already synthesized above --
                        # re-synthesizing it cost a second Sarvam call and ~2s on every hangup.
                        # Only the max-turns sign-off is new text that needs TTS.
                        if not is_ending:
                                audio_cache[call_sid] = [await manager.generate_tts(
                                        text="Thanks for chatting with us! Our team will be in touch shortly. Goodbye!",
                                        language=target_lang,
                                )]
                        plays = _play_tags(client, call_sid)
                        
                        # Cleanup
                        del call_sessions[call_sid]
                        
                        if settings.live_transfer_enabled and assigned_rm and assigned_rm.phone:
                                # <Dial> only falls through to <Hangup/> when the RM does not answer
                                logger.info(f"[TRANSFER] Bridging call {call_sid} to RM {assigned_rm.name}")
                                return _xml_response(
                                        f'<Response>{plays}'
                                        f'<Dial timeout="{settings.live_transfer_timeout_seconds}" '
                                        f'callerId="{xml_escape(settings.twilio_phone_number)}">'
                                        f'<Number>{xml_escape(assigned_rm.phone)}</Number></Dial><Hangup/></Response>'
                                )
                        return _xml_response(f'<Response>{plays}<Hangup/></Response>')
                
                # 7. Build returning TwiML with next recording
                plays = _play_tags(client, call_sid)
                # Carry the session in the URL: the in-process call_sessions cache is
                # lost on a restart/reload or when another API process takes the turn,
                # and a missing session makes the webhook create a bogus lead.
                record_path = "/api/webhook/twilio/recording"
                if session_id and lead_id:
                        record_path += f"?session_id={session_id}&lead_id={lead_id}"
                record_url = client.build_base_url(record_path)
                
                # Update turn count
                call_sessions[call_sid]["turn_count"] = turn_count
                
                twiml = f'''<Response>
                    {plays}
                    <Record action="{xml_escape(record_url)}" method="POST" playBeep="true" maxLength="60" timeout="2" trim="trim-silence" />
                </Response>'''
                
                return _xml_response(twiml)

        except Exception as exc:  # pragma: no cover
                logger.exception("Failed to process full Twilio conversational turn: %s", exc)
                return Response(
                        content=client.build_say_twiml("Sorry, I could not process your input just now. Please speak again."),
                        media_type="application/xml",
                )

def _play_tags(client, call_sid: str) -> str:
    """One <Play> per synthesized chunk, in order. Twilio plays them back to back."""
    count = max(1, len(audio_cache.get(call_sid) or [1]))
    return "".join(
        f"<Play>{xml_escape(client.build_base_url(f'/api/webhook/twilio/audio/{call_sid}/{i}'))}</Play>"
        for i in range(count)
    )


# No auth dependency: Twilio fetches this URL itself from <Play> and cannot send a
# bearer token, nor does it sign media fetches (only webhook callbacks are signed).
# Gating it broke every call -- Twilio got a 401, could not play the reply, and hung up.
def _empty_audio() -> Response:
        """A fresh Response each time: one instance must not be shared across requests."""
        return Response(content=b"", media_type="audio/wav")


# A chunk Twilio is about to play is normally already done; this only covers the
# case where the previous chunk was shorter than the next one took to synthesize.
CHUNK_WAIT_SECONDS = 10


async def _chunk_bytes(call_sid: str, index: int) -> Optional[bytes]:
        chunks = audio_cache.get(call_sid)
        if not chunks or index >= len(chunks):
                return None

        item = chunks[index]
        if isinstance(item, (bytes, bytearray)):
                return bytes(item)

        # still synthesizing: wait for it rather than return silence and lose the words
        try:
                data = await asyncio.wait_for(asyncio.shield(item), timeout=CHUNK_WAIT_SECONDS)
        except Exception as exc:
                logger.warning("Chunk %s for %s never arrived: %s", index, call_sid, exc)
                return None

        current = audio_cache.get(call_sid)
        if current is not None and index < len(current):
                current[index] = data  # memoize so a Twilio retry is served instantly
        return data


@router.get("/audio/{call_sid}")
async def fetch_audio(call_sid: str) -> Response:
        """Endpoint for Twilio <Play> to fetch the generated audio bytes."""
        return await fetch_audio_chunk(call_sid, 0)


@router.get("/audio/{call_sid}/{index}")
async def fetch_audio_chunk(call_sid: str, index: int) -> Response:
        """One chunk of the reply, awaited if it is still being synthesized."""
        data = await _chunk_bytes(call_sid, index)
        if not data:
                logger.error(f"No audio found in cache for CallSid: {call_sid} (chunk {index})")
                # Empty response so Twilio skips silently instead of failing the call
                return _empty_audio()

        return Response(content=data, media_type="audio/wav")

@router.post("/status", dependencies=[Depends(verify_twilio_signature)])
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
                logger.warning(f"[TWILIO STATUS] Call {call_sid} failed or hit voicemail. Parking lead as FOLLOW_UP...")
                if lead_id:
                        db_client = None
                        try:
                                db_client = await get_db_client()
                                repository = Repository(db_client)
                                # There is no FAILED status. FOLLOW_UP keeps the lead out of the
                                # NEW pool, so the dialer does not hammer a number that did not answer.
                                await repository.update_lead(
                                        lead_id=UUID(lead_id),
                                        status=LeadStatus.FOLLOW_UP.value
                                )
                                logger.info(f"[TWILIO STATUS] Marked lead {lead_id} as FOLLOW_UP")
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
                                        # Classify from what the caller actually said (WARM if no clear signal)
                                        call_session = await repository.get_call_session(UUID(session_id))
                                        history = (call_session or {}).get("conversation_history", [])
                                        if not user_texts_from_history(history):
                                                # Answered but never spoke (hung up in the greeting): there is
                                                # nothing to score, so do not invent an outcome.
                                                await repository.update_lead(
                                                        lead_id=UUID(lead_id),
                                                        status=LeadStatus.FOLLOW_UP.value
                                                )
                                                logger.info(f"[TWILIO STATUS] Lead {lead_id} said nothing; marked FOLLOW_UP")
                                                return Response(content="<Response></Response>", media_type="application/xml")
                                        outcome = classify_outcome(user_texts_from_history(history))
                                        logger.info(f"[TWILIO STATUS] Lead {lead_id} hung up abruptly. Auto-scoring as {outcome}...")
                                        queue_manager = QueueManager()
                                        scoring_engine = ScoringEngine(repository)
                                        await _score_and_assign_lead(
                                                lead_id=UUID(lead_id),
                                                session_id=UUID(session_id),
                                                repository=repository,
                                                scoring_engine=scoring_engine,
                                                queue_manager=queue_manager,
                                                classification_override=outcome
                                        )
                        except Exception as e:
                                logger.error(f"[TWILIO STATUS] Error auto-scoring on hangup: {e}")
        
        # Always return HTTP 200 to Twilio
        return Response(content="<Response></Response>", media_type="application/xml")
