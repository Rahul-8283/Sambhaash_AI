import logging

from config import get_config
from services.tts.sarvam_service import SarvamTTSService
from services.tts.audio_formatter import AudioFormatter

logger = logging.getLogger(__name__)


class CallManager:
    """Turns reply text into Twilio-ready audio (Sarvam TTS + 8kHz WAV formatting)."""

    def __init__(self):
        settings = get_config()
        self.tts_service = SarvamTTSService(api_key=settings.sarvam_api_key)
        self.formatter = AudioFormatter()

    async def generate_tts(self, text: str, language: str) -> bytes:
        logger.info(f"Generating TTS for language {language}: {text[:30]}...")
        # 'kavya' works well for bulbul:v3
        raw_audio = await self.tts_service.generate_speech(text=text, language=language, speaker="kavya")
        return self.formatter.format_for_twilio(raw_audio)
