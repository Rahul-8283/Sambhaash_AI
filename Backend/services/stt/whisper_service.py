from __future__ import annotations

import logging
from io import BytesIO
from typing import Optional

import requests

from utils.language import to_language_code
from openai import OpenAI

from config import get_config


logger = logging.getLogger(__name__)


# ISO codes Whisper accepts that the platform speaks
WHISPER_LANGUAGES = {"en", "hi", "mr", "bn", "pa", "gu", "ta", "te", "kn", "ml"}

_twilio_media_session = requests.Session()


class WhisperService:
	"""Speech-to-text service using Groq Whisper."""

	def __init__(self, api_key: str | None = None) -> None:
		self.settings = get_config()
		resolved_key = api_key or self.settings.groq_api_key
		if not resolved_key or resolved_key == "sk-test-default":
			raise ValueError("GROQ_API_KEY is missing in the backend env file.")
		self.client = OpenAI(
			api_key=resolved_key,
			base_url="https://api.groq.com/openai/v1"
		)

	def transcribe_audio_bytes(self, audio_bytes: bytes, filename: str = "recording.mp3", language: Optional[str] = None) -> str:
		"""Transcribe raw audio bytes using Groq Whisper."""

		audio_file = BytesIO(audio_bytes)
		audio_file.name = filename

		kwargs: dict[str, object] = {
			"model": self.settings.stt_model_name,
			"file": audio_file,
		}

		# A hint skips auto-detection (faster, and more accurate on short clips).
		# Odia is not a Whisper language, so it falls back to auto-detect.
		code = to_language_code(language, default="") if language else ""
		if code in WHISPER_LANGUAGES:
			kwargs["language"] = code

		result = self.client.audio.transcriptions.create(**kwargs)
		text = getattr(result, "text", None) or ""
		return text.strip()

	def transcribe_recording_url(
		self,
		recording_url: str,
		twilio_account_sid: str,
		twilio_auth_token: str,
		language: Optional[str] = None,
	) -> str:
		"""Download a Twilio recording and transcribe it."""

		url = recording_url if recording_url.endswith((".mp3", ".wav")) else f"{recording_url}.mp3"
		# Shared session keeps the connection to Twilio's media host alive between turns
		response = _twilio_media_session.get(url, auth=(twilio_account_sid, twilio_auth_token), timeout=30)
		response.raise_for_status()
		return self.transcribe_audio_bytes(response.content, filename="twilio_recording.mp3", language=language)
