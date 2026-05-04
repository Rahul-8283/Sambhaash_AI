# scripts/test_call.py or services/telephony/call_manager.py
import asyncio
import os
from dotenv import load_dotenv
from services.tts.sarvam_service import SarvamTTSService
from services.tts.audio_formatter import AudioFormatter

# Load keys for local testing
load_dotenv() 

async def generate_twilio_response(text: str, language: str = "en"):
    """
    Complete pipeline: LLM string output -> Sarvam AI -> Twilio Wrapper
    """
    tts_service = SarvamTTSService()
    formatter = AudioFormatter()
    
    try:
        # Step 1: Fetch audio bytes asynchronously from Sarvam
        print(f"Generating speech for text: '{text}'...")
        raw_audio = await tts_service.generate_speech(
            text=text, 
            language=language, 
            speaker="kavya"
        )
        
        # Step 2: Format bytes into strictly typed WAV for Twilio
        print("Formatting audio specifically for Twilio...")
        twilio_ready_wav = formatter.format_for_twilio(raw_audio)
        
        # Step 3: (Validation) - Write to disk to test playback locally
        test_filename = "test_output_twilio.wav"
        with open(test_filename, "wb") as f:
            f.write(twilio_ready_wav)
            
        print(f"Success! Audio ready and written to {test_filename}")
        
        # Actual System Return Value: 
        # (This would get streamed via WebSockets or saved to an S3 bucket 
        # that Twilio grabs via a <Play> TwiML URL)
        return twilio_ready_wav
        
    except Exception as e:
        print(f"TTS Pipeline Error: {e}")

if __name__ == "__main__":
    # Test text (Hi, I am calling from Sambhash AI)
    test_text = "आज का दिन बहुत बड़ा दिन है"
    asyncio.run(generate_twilio_response(test_text, language="hi"))