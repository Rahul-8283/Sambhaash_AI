from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request
from fastapi.responses import Response

from Backend.config import get_settings
from Backend.services.stt.language_detector import LanguageDetector
from Backend.services.stt.whisper_service import WhisperService
from Backend.services.telephony.twilio_client import TwilioClient


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhook/twilio", tags=["Twilio Webhooks"])


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
	"""Receive a Twilio recording, transcribe it, and classify the language."""

	settings = get_settings()
	form = await request.form()
	form_data = dict(form)

	recording_url = _form_value(form_data, "RecordingUrl")
	call_sid = _form_value(form_data, "CallSid", "")
	from_number = _form_value(form_data, "From", "")
	duration = _form_value(form_data, "RecordingDuration", "0")

	if not recording_url:
		logger.warning("Recording webhook called without RecordingUrl (CallSid=%s)", call_sid)
		return Response(
			content=TwilioClient().build_say_twiml("We did not receive any audio. Please try again."),
			media_type="application/xml",
		)

	client = TwilioClient()
	stt = WhisperService()
	language_detector = LanguageDetector()

	if not client.configured:
		logger.error("Twilio credentials are not configured in backend/env")
		return Response(
			content=client.build_say_twiml("We are having trouble connecting right now. Please call again later."),
			media_type="application/xml",
		)

	try:
		transcript = stt.transcribe_recording_url(
			recording_url=recording_url,
			twilio_account_sid=settings.TWILIO_ACCOUNT_SID or "",
			twilio_auth_token=settings.TWILIO_AUTH_TOKEN or "",
		)
		language = language_detector.detect_language(transcript)
		payload = {
			"call_sid": call_sid,
			"from_number": from_number,
			"recording_url": recording_url,
			"recording_duration": duration,
			"text": transcript,
			"language": language,
		}
		logger.info("Person 1 payload ready: %s", payload)

		acknowledgement = client.build_say_twiml(
			"Thanks. We got your message and our assistant will continue from here."
		)
		return Response(content=acknowledgement, media_type="application/xml")
	except Exception as exc:  # pragma: no cover - external API/network failures
		logger.exception("Failed to process Twilio recording: %s", exc)
		return Response(
			content=client.build_say_twiml("Sorry, I could not process your audio just now. Please try again."),
			media_type="application/xml",
		)


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
