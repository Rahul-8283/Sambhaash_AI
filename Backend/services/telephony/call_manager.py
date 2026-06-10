import asyncio
import logging
from typing import Tuple, Optional, Dict, Any

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
        
        # Instantiate LLM Client using Groq
        self.llm_client = LLMClient(
            model_name="llama-3.3-70b-versatile",
            api_key=settings.groq_api_key or "",
            base_url="https://api.groq.com/openai/v1"
        )
        
        # Orchestrator uses the LLM client
        self.orchestrator = Orchestrator(llm_callable=self.llm_client)
        
        # Instantiate TTS and Formatter
        self.tts_service = SarvamTTSService(api_key=settings.sarvam_api_key)
        self.formatter = AudioFormatter()

    async def process_turn(
        self,
        call_sid: str,
        user_text: str,
        language: str,
        kb_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str, bool]:
        '''
        Takes transcribed text, processes with LLM (with optional KB context), 
        and returns the response text and suggested playback language.
        
        Args:
            call_sid: Twilio call SID
            user_text: Transcribed user message
            language: Detected language
            kb_context: Optional KB context from retrieve_context_for_call()
        
        Returns:
            (reply_text, language, is_ending) tuple
        '''
        request_obj = OrchestrationRequest(
            lead_id=call_sid,
            user_text=user_text,
            language=language,
            session_id=call_sid,
            metadata={
                "kb_context": kb_context if kb_context else {},
                "kb_available": kb_context.get("kb_available", False) if kb_context else False
            }
        )
        
        logger.info(f"Processing turn for call {call_sid} with text: {user_text}")
        if kb_context and kb_context.get("kb_available"):
            logger.info(f"KB Context: {len(kb_context.get('context_blocks', []))} chunks injected")
        
        # Run blocking orchestrator in a thread so FastAPI stays async/non-blocking
        try:
            result = await asyncio.to_thread(self.orchestrator.process_turn, request_obj)
            is_ending = result.stage in ["handoff", "closing", "follow_up"] or getattr(result, "handoff_required", False)
            return result.reply_text, result.language, is_ending
        except Exception as e:
            logger.exception("LLM Orchestration failed")
            # Provide an automatic fallback response so the call doesn't drop
            return "I'm sorry, I'm having a little trouble connecting right now. Can you repeat that?", language, False

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
