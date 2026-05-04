from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request
from fastapi.responses import Response

from config import get_config
from services.stt.language_detector import LanguageDetector
from services.stt.whisper_service import WhisperService
from services.telephony.twilio_client import TwilioClient
from services.telephony.call_manager import CallManager


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhook/twilio", tags=["Twilio Webhooks"])

# Simple in-memory cache to hold generated audio for Twilio to fetch via TwiML <Play>
# In production, use Redis or S3 for multi-worker scaling
audio_cache: dict[str, bytes] = {}

def _xml_response(xml: str) -> Response:
        return Response(content=xml, media_type="application/xml")


def _form_value(form: Dict[str, Any], key: str, default: Optional[str] = None) -> Optional[str]:
        value = form.get(key, default)
        return str(value) if value is not None else None


@router.api_route("/voice", methods=["GET", "POST"])
async def voice_webhook(request: Request) -> Response:
        """Initial Twilio Voice webhook for inbound calls."""

        form = await request.form() if request.method == "POST" else {}
        caller = _form_value(dict(form), "From", "unknown")
        logger.info("Inbound voice webhook received from %s", caller)

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

        try:
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

                # 3. TTS Generation
                audio_bytes = await manager.generate_tts(text=reply_text, language=target_lang)
                
                # 4. Cache audio bytes for Twilio <Play> fetch
                audio_cache[call_sid] = audio_bytes

                # 5. Build returning TwiML
                # We use <Play> pointing to our /audio route, followed by another <Record>
                audio_url = client.build_base_url(f"/api/webhook/twilio/audio/{call_sid}")
                record_url = client.build_base_url("/api/webhook/twilio/recording")
                
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
                "Thanks for messaging Sambhaash AI. Your request is received and will be processed by the team."
        )
        return Response(content=reply, media_type="application/xml")
