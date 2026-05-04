import io
import wave
import logging

logger = logging.getLogger(__name__)

class AudioFormatter:
    """
    Handles formatting of audio bytes for compatibility with Twilio/Telephony endpoints.
    Required format: WAV, 8000 Hz, Mono, 16-bit PCM.
    """

    @staticmethod
    def format_for_twilio(raw_audio_bytes: bytes) -> bytes:
        if not raw_audio_bytes:
            logger.error("Received empty audio bytes for formatting.")
            raise ValueError("Audio bytes cannot be empty")

        # Because Sarvam AI gives us 8000Hz naturally if requested, 
        # we can just validate the wave headers without importing Pydub!
        try:
            with wave.open(io.BytesIO(raw_audio_bytes), 'rb') as wf:
                channels = wf.getnchannels()
                sample_width = wf.getsampwidth()
                frame_rate = wf.getframerate()
                
                logger.info(f"Audio details - Channels: {channels}, Width: {sample_width} bytes, Rate: {frame_rate}Hz")
                
                if channels != 1 or sample_width != 2 or frame_rate != 8000:
                    logger.warning("Audio is not strictly 8000Hz 16-bit Mono. Audio quality on Twilio might degrade.")
            
            return raw_audio_bytes
            
        except wave.Error as e:
            logger.error("Failed to read audio as WAV. Data might be corrupt.")
            raise Exception("Invalid or corrupted WAV audio data received")
