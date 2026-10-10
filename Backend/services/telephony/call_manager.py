import asyncio
import io
import logging
import re
import wave
from typing import List

from config import get_config
from services.tts.sarvam_service import SarvamTTSService
from services.tts.audio_formatter import AudioFormatter

logger = logging.getLogger(__name__)

# Sentence ends in Latin and Devanagari/Indic scripts
_SENTENCE_END = re.compile(r"(?<=[.!?।])\s+")
# Below this, one request is as fast as two
_MIN_SPLIT_CHARS = 60


def split_for_tts(text: str) -> List[str]:
    """
    Split a reply into two roughly equal halves at a sentence boundary.

    TTS time grows with text length, so synthesizing the halves in parallel and
    joining them is markedly faster than one request for the whole reply.
    """
    text = text.strip()
    sentences = [s for s in _SENTENCE_END.split(text) if s]
    if len(text) < _MIN_SPLIT_CHARS or len(sentences) < 2:
        return [text]

    # The cut that makes the two halves closest in length (the slower half sets the time)
    lengths = [len(x) for x in sentences]
    cut = min(
        range(1, len(sentences)),
        key=lambda i: abs(sum(lengths[:i]) - sum(lengths[i:])),
    )
    return [" ".join(sentences[:cut]), " ".join(sentences[cut:])]


def join_wavs(parts: List[bytes]) -> bytes:
    """Concatenate WAV files that share one format into a single WAV."""
    if len(parts) == 1:
        return parts[0]
    out = io.BytesIO()
    params = None
    with wave.open(out, "wb") as writer:
        for blob in parts:
            with wave.open(io.BytesIO(blob), "rb") as reader:
                if params is None:
                    params = reader.getparams()
                    writer.setparams(params)
                elif reader.getparams()[:3] != params[:3]:
                    raise ValueError("WAV parts differ in format")
                writer.writeframes(reader.readframes(reader.getnframes()))
    return out.getvalue()


class CallManager:
    """Turns reply text into Twilio-ready audio (Sarvam TTS + 8kHz WAV formatting)."""

    def __init__(self):
        settings = get_config()
        self.tts_service = SarvamTTSService(api_key=settings.sarvam_api_key)
        self.formatter = AudioFormatter()

    async def _synthesize(self, text: str, language: str) -> bytes:
        # 'kavya' works well for bulbul:v3
        return await self.tts_service.generate_speech(text=text, language=language, speaker="kavya")

    async def generate_tts(self, text: str, language: str) -> bytes:
        logger.info(f"Generating TTS for language {language}: {text[:30]}...")
        chunks = split_for_tts(text)

        if len(chunks) > 1:
            try:
                parts = await asyncio.gather(*[self._synthesize(c, language) for c in chunks])
                return self.formatter.format_for_twilio(join_wavs(list(parts)))
            except Exception as e:
                logger.warning(f"Parallel TTS failed, falling back to a single request: {e}")

        return self.formatter.format_for_twilio(await self._synthesize(text, language))
