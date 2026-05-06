from __future__ import annotations

import logging
from io import BytesIO
from typing import Optional

import requests
from openai import OpenAI

from config import get_config


logger = logging.getLogger(__name__)


class WhisperService:
	"""Speech-to-text service using OpenAI Whisper with automatic Groq fallback."""

	def __init__(self, api_key: str | None = None) -> None:
		self.settings = get_config()
		resolved_key = api_key or self.settings.openai_api_key
		if not resolved_key:
			raise ValueError("OPENAI_API_KEY is missing in the backend env file.")
		self.client = OpenAI(api_key=resolved_key)

		# Lazy initialize Groq fallback client
		self.groq_client = None
		if self.settings.groq_api_key and self.settings.groq_api_key != "sk-test-default":
			try:
				self.groq_client = OpenAI(
					api_key=self.settings.groq_api_key,
					base_url="https://api.groq.com/openai/v1"
				)
				logger.info("[STT] Initialized Groq Whisper fallback client.")
			except Exception as e:
				logger.warning(f"[STT] Failed to initialize Groq client: {e}")

	def transcribe_audio_bytes(self, audio_bytes: bytes, filename: str = "recording.mp3", language: Optional[str] = None) -> str:
		"""Transcribe raw audio bytes using Whisper (OpenAI or Groq fallback)."""

		audio_file = BytesIO(audio_bytes)
		audio_file.name = filename

		kwargs: dict[str, object] = {
			"model": "whisper-1",
			"file": audio_file,
		}

		if language:
			normalized_language = language.lower().strip()
			if normalized_language in {"english", "en"}:
				kwargs["language"] = "en"
			elif normalized_language in {"hindi", "hi"}:
				kwargs["language"] = "hi"

		try:
			result = self.client.audio.transcriptions.create(**kwargs)
			text = getattr(result, "text", None) or ""
			return text.strip()
		except Exception as e:
			logger.warning(f"[STT] OpenAI Whisper transcription failed: {e}. Trying Groq fallback...")
			if self.groq_client:
				try:
					audio_file.seek(0)
					kwargs["model"] = "whisper-large-v3"
					kwargs["file"] = audio_file
					result = self.groq_client.audio.transcriptions.create(**kwargs)
					text = getattr(result, "text", None) or ""
					logger.info("[STT] ✅ Successfully transcribed using Groq Whisper-large-v3 fallback!")
					return text.strip()
				except Exception as ge:
					logger.error(f"[STT] Groq Whisper fallback also failed: {ge}")
					raise e
			else:
				raise e

	def transcribe_recording_url(
		self,
		recording_url: str,
		twilio_account_sid: str,
		twilio_auth_token: str,
		language: Optional[str] = None,
	) -> str:
		"""Download a Twilio recording and transcribe it."""

		url = recording_url if recording_url.endswith((".mp3", ".wav")) else f"{recording_url}.mp3"
		response = requests.get(url, auth=(twilio_account_sid, twilio_auth_token), timeout=30)
		response.raise_for_status()
		return self.transcribe_audio_bytes(response.content, filename="twilio_recording.mp3", language=language)
