from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import urljoin
from xml.sax.saxutils import escape

import requests

from config import get_config


logger = logging.getLogger(__name__)

TWILIO_API_BASE = "https://api.twilio.com/2010-04-01"


def _xml_response(inner_xml: str) -> str:
	return f"<?xml version=\"1.0\" encoding=\"UTF-8\"?><Response>{inner_xml}</Response>"


def _safe_text(value: str) -> str:
	return escape(value or "")


@dataclass(slots=True)
class TwilioCallResult:
	sid: Optional[str]
	status: str
	raw: dict[str, Any]


class TwilioClient:
	"""Minimal Twilio helper for inbound voice, outbound calls, and WhatsApp sandbox messages."""

	def __init__(
		self,
		account_sid: str | None = None,
		auth_token: str | None = None,
		phone_number: str | None = None,
		whatsapp_from: str | None = None,
		webhook_base_url: str | None = None,
	) -> None:
		self.settings = get_config()
		self.account_sid = account_sid or self.settings.twilio_account_sid
		self.auth_token = auth_token or self.settings.twilio_auth_token
		self.phone_number = phone_number or self.settings.twilio_phone_number
		self.whatsapp_from = whatsapp_from or self.settings.twilio_whatsapp_from
		self.webhook_base_url = webhook_base_url or self.settings.twilio_webhook_base_url

	@property
	def configured(self) -> bool:
		return bool(self.account_sid and self.auth_token and self.phone_number)

	def _auth(self) -> tuple[str, str]:
		if not self.account_sid or not self.auth_token:
			raise ValueError("Twilio credentials are missing in the backend env file.")
		return self.account_sid, self.auth_token

	def build_base_url(self, path: str) -> str:
		if path.startswith("http://") or path.startswith("https://"):
			return path
		if self.webhook_base_url:
			return urljoin(self.webhook_base_url.rstrip("/") + "/", path.lstrip("/"))
		return path

	def build_voice_entry_twiml(
		self,
		greeting_text: str = "Hello from Sambhaash AI. Please speak after the beep.",
		recording_callback_path: str = "/api/webhook/twilio/recording",
		timeout_seconds: int = 60,
	) -> str:
		callback_url = self.build_base_url(recording_callback_path)
		inner_xml = (
			f'<Say voice="alice">{_safe_text(greeting_text)}</Say>'
			f'<Record action="{_safe_text(callback_url)}" '
			f'method="POST" playBeep="true" maxLength="{int(timeout_seconds)}" '
			f'trim="trim-silence" />'
			'<Say voice="alice">Sorry, I could not hear anything. Please call again.</Say>'
		)
		return _xml_response(inner_xml)

	def build_whatsapp_reply_twiml(self, body: str) -> str:
		return _xml_response(f'<Message>{_safe_text(body)}</Message>')

	def build_say_twiml(self, body: str) -> str:
		return _xml_response(f'<Say voice="alice">{_safe_text(body)}</Say>')

	def download_recording(self, recording_url: str) -> bytes:
		"""Download a Twilio recording as audio bytes."""

		url = recording_url if recording_url.endswith((".mp3", ".wav")) else f"{recording_url}.mp3"
		response = requests.get(url, auth=self._auth(), timeout=30)
		response.raise_for_status()
		return response.content

	def create_outbound_call(self, to_number: str, webhook_path: str = "/api/webhook/twilio/voice") -> TwilioCallResult:
		"""Start an outbound call that points Twilio back to this backend."""

		callback_url = self.build_base_url(webhook_path)
		payload = {
			"To": to_number,
			"From": self.phone_number,
			"Url": callback_url,
			"Method": "POST",
		}
		response = requests.post(
			f"{TWILIO_API_BASE}/Accounts/{self._auth()[0]}/Calls.json",
			data=payload,
			auth=self._auth(),
			timeout=30,
		)
		response.raise_for_status()
		data = response.json()
		return TwilioCallResult(sid=data.get("sid"), status=data.get("status", "unknown"), raw=data)

	def send_whatsapp_message(self, to_number: str, body: str) -> dict[str, Any]:
		"""Send a WhatsApp message through the Twilio sandbox."""

		if not self.whatsapp_from:
			raise ValueError("TWILIO_WHATSAPP_FROM is missing in the backend env file.")

		payload = {
			"From": self.whatsapp_from,
			"To": to_number if to_number.startswith("whatsapp:") else f"whatsapp:{to_number}",
			"Body": body,
		}
		response = requests.post(
			f"{TWILIO_API_BASE}/Accounts/{self._auth()[0]}/Messages.json",
			data=payload,
			auth=self._auth(),
			timeout=30,
		)
		response.raise_for_status()
		return response.json()
