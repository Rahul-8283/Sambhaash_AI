from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent


def _load_backend_env() -> None:
	"""Load the shared backend env file if it exists."""

	for candidate in (
		BASE_DIR / "env",
		BASE_DIR / ".env",
		BASE_DIR.parent / ".env",
	):
		if candidate.exists():
			load_dotenv(candidate, override=False)
			break


_load_backend_env()


class Settings(BaseSettings):
	"""Application settings backed by the shared backend environment."""

	model_config = SettingsConfigDict(extra="ignore")

	MODE: str = "development"
	BACKEND_HOST: str = "0.0.0.0"
	BACKEND_PORT: int = 8000

	# Core AI / STT credentials
	OPENAI_API_KEY: Optional[str] = None
	GROQ_API_KEY: Optional[str] = None
	SARVAM_API_KEY: Optional[str] = None

	# Twilio credentials
	TWILIO_ACCOUNT_SID: Optional[str] = None
	TWILIO_AUTH_TOKEN: Optional[str] = None
	TWILIO_PHONE_NUMBER: Optional[str] = None
	TWILIO_WHATSAPP_FROM: Optional[str] = None

	# Infra / storage
	SUPABASE_URL: Optional[str] = None
	SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
	DATABASE_URL: Optional[str] = None
	REDIS_URL: Optional[str] = None

	# Optional deployment helper for Twilio webhooks
	TWILIO_WEBHOOK_BASE_URL: Optional[str] = None

	@property
	def has_twilio(self) -> bool:
		return bool(
			self.TWILIO_ACCOUNT_SID
			and self.TWILIO_AUTH_TOKEN
			and self.TWILIO_PHONE_NUMBER
		)

	@property
	def has_openai(self) -> bool:
		return bool(self.OPENAI_API_KEY)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
	return Settings()


settings = get_settings()
