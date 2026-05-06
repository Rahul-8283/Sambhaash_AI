import os
import httpx
import base64
import logging
from typing import Optional

# Setup basic logger if not configured
logger = logging.getLogger(__name__)

class SarvamTTSService:
    """
    Service for interacting with Sarvam AI's Text-to-Speech API.
    Designed for async execution to minimize blocking during active calls.
    """
    
    BASE_URL = "https://api.sarvam.ai/text-to-speech"
    
    # Map simple language codes to Sarvam's internal codes
    LANGUAGE_MAP = {
        "en": "en-IN",
        "hi": "hi-IN",
        "te": "te-IN",
        "ta": "ta-IN",
        "bn": "bn-IN",
        "kn": "kn-IN",
        "ml": "ml-IN",
        "mr": "mr-IN",
        "or": "or-IN",
        "pa": "pa-IN",
        "gu": "gu-IN"
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the TTS service. Will attempt to load from environment if not passed.
        """
        self.api_key = api_key or os.getenv("SARVAM_API_KEY")
        if not self.api_key:
            logger.error("SARVAM_API_KEY is missing. TTS will fail.")
            raise ValueError("SARVAM_API_KEY environment variable is not set")
            
        self.headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json"
        }

    async def generate_speech(self, text: str, language: str = "en", speaker: str = "kavya") -> bytes:
        """
        Convert text to speech async.
        
        Args:
            text: The string to convert.
            language: ISO 639-1 code (en, hi, te).
            speaker: The speaker voice (e.g. 'kavya', 'rita').
            
        Returns:
            bytes: Raw audio bytes.
        """
        target_language = self.LANGUAGE_MAP.get(language.lower(), "en-IN")
        
        payload = {
            "inputs": [text],
            "target_language_code": target_language,
            "speaker": speaker,
            "pace": 1.0,
            "speech_sample_rate": 8000,
            "enable_preprocessing": True,
            "model": "bulbul:v3"
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                logger.debug(f"Requesting Sarvam TTS for text: {text[:20]}... in {target_language}")
                response = await client.post(
                    self.BASE_URL, 
                    json=payload, 
                    headers=self.headers
                )
                response.raise_for_status()
                
                data = response.json()
                base64_audio = data["audios"][0]
                audio_bytes = base64.b64decode(base64_audio)
                
                logger.info(f"Successfully generated {len(audio_bytes)} bytes of audio")
                return audio_bytes
                
            except httpx.ReadTimeout:
                logger.error("Sarvam TTS API timed out.")
                raise Exception("TTS Generation timeout")
            except httpx.HTTPStatusError as e:
                logger.error(f"Sarvam API gave {e.response.status_code}: {e.response.text}")
                raise Exception(f"TTS API Error: {e.response.status_code}")
            except Exception as e:
                logger.error(f"Unexpected error in TTS generation: {str(e)}")
                raise e