import asyncio
import logging
from typing import Tuple

from config import get_config
from services.llm import Orchestrator, OrchestrationRequest, LLMClient
from services.tts.sarvam_service import SarvamTTSService
from services.tts.audio_formatter import AudioFormatter

logger = logging.getLogger(__name__)

class CallManager:
    '''
    Manages the full lifecycle of a Twilio voice turn.
    Coordinates between LLM (Orchestrator), TTS (Sarvam), and Twilio formatting.
    '''
    def __init__(self):
        settings = get_config()
        
        # Instantiate LLM Client (OpenAI via our blocking client)
        self.llm_client = LLMClient(
            model_name="gpt-4o-mini",
            api_key=settings.openai_api_key or ""
        )
        
        # Orchestrator uses the LLM client
        self.orchestrator = Orchestrator(llm_adapter=self.llm_client)
        
        # Instantiate TTS and Formatter
        self.tts_service = SarvamTTSService(api_key=settings.sarvam_api_key)
        self.formatter = AudioFormatter()

    async def process_turn(self, call_sid: str, user_text: str, language: str) -> Tuple[str, str]:
        '''
        Takes transcribed text, processes with LLM, and returns the response text and suggested playback language.
        '''
        request_obj = OrchestrationRequest(
            lead_id=call_sid, # use call_sid as connection ID
            user_text=user_text,
            language=language,
            session_id=call_sid
        )
        
        logger.info(f"Processing turn for call {call_sid} with text: {user_text}")
        
        # Run blocking orchestrator in a thread so FastAPI stays async/non-blocking
        try:
            result = await asyncio.to_thread(self.orchestrator.process_turn, request_obj)
            return result.reply_text, result.language
        except Exception as e:
            logger.exception("LLM Orchestration failed")
            # Provide an automatic fallback response so the call doesn't drop
            return "I'm sorry, I'm having a little trouble connecting right now. Can you repeat that?", language

    async def generate_tts(self, text: str, language: str) -> bytes:
        '''
        Converts text to Twilio-ready audio bytes via Sarvam TTS.
        '''
        logger.info(f"Generating TTS for language {language}: {text[:30]}...")
        # Since we recently found 'kavya' works well for bulbul:v3
        raw_audio = await self.tts_service.generate_speech(text=text, language=language, speaker="kavya")
        
        # Format the bytes strictly for Twilio playback (8kHz WAV)
        twilio_ready_wav = self.formatter.format_for_twilio(raw_audio)
        return twilio_ready_wav
