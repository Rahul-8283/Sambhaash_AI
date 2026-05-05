"""
Call Recording Service (Phase 2B)
Handles recording storage, transcription, and analysis
"""

import logging
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime
import json

from config import settings
from services.database.supabase_client import SupabaseClient
from services.database.repository import Repository
from services.storage_client import SupabaseStorageClient
from services.stt.whisper_service import WhisperService

logger = logging.getLogger(__name__)


class CallRecordingService:
    """
    Service for handling call recordings.
    
    Responsibilities:
    - Download recording from Twilio
    - Save to Supabase Storage
    - Transcribe using Whisper
    - Extract key topics/sentiment
    - Store metadata in database
    """
    
    def __init__(
        self,
        db_client: Optional[SupabaseClient] = None,
        storage_client: Optional[SupabaseStorageClient] = None
    ):
        self.db_client = db_client
        self.storage_client = storage_client
        self.repository: Optional[Repository] = None
        self.whisper_service = WhisperService()
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Lazy initialization of clients"""
        if self._initialized:
            return
        
        if not self.db_client:
            from services.database.supabase_client import get_db_client
            self.db_client = await get_db_client()
        
        if not self.storage_client:
            from services.storage_client import get_storage_client
            self.storage_client = await get_storage_client()
        
        if not self.repository:
            self.repository = Repository(self.db_client)
        
        self._initialized = True
    
    async def save_call_recording(
        self,
        call_session_id: UUID,
        recording_url: str,
        twilio_recording_sid: str,
        twilio_call_sid: str,
        duration_seconds: int = 0,
        recorded_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Download recording from Twilio, save to storage, transcribe, and store metadata.
        
        Args:
            call_session_id: Call session ID
            recording_url: URL to Twilio recording
            twilio_recording_sid: Twilio recording SID
            twilio_call_sid: Twilio call SID
            duration_seconds: Call duration
            recorded_at: When recording was made
        
        Returns:
            Dict with recording metadata and transcription
        """
        await self._ensure_initialized()
        
        try:
            logger.info(f"[RECORDING] Starting save process for call {call_session_id}")
            
            if not recorded_at:
                recorded_at = datetime.utcnow()
            
            # Step 1: Download recording from Twilio
            logger.info(f"[RECORDING] Downloading from Twilio: {recording_url}")
            recording_bytes = await self._download_recording(recording_url)
            
            if not recording_bytes:
                logger.error("[RECORDING] Failed to download recording")
                return {"error": "Failed to download recording"}
            
            file_size = len(recording_bytes)
            logger.info(f"[RECORDING] Downloaded {file_size} bytes")
            
            # Step 2: Save to Supabase Storage
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            storage_path = f"recordings/{timestamp}_{call_session_id}.wav"
            
            logger.info(f"[RECORDING] Uploading to storage: {storage_path}")
            storage_result = await self.storage_client.upload_file(
                file_path=storage_path,
                file_content=recording_bytes,
                content_type="audio/wav"
            )
            storage_url = storage_result.get("public_url", "")
            logger.info(f"[RECORDING] Stored at: {storage_url}")
            
            # Step 3: Transcribe using Whisper
            logger.info(f"[RECORDING] Transcribing audio...")
            transcription = await self._transcribe_recording(recording_bytes)
            
            # Step 4: Extract metadata
            key_topics = self._extract_topics(transcription.get("text", ""))
            sentiment = self._analyze_sentiment(transcription.get("text", ""))
            
            # Step 5: Save to database
            logger.info(f"[RECORDING] Saving metadata to database")
            recording_record = await self.repository.create_call_recording(
                call_session_id=call_session_id,
                twilio_recording_sid=twilio_recording_sid,
                twilio_call_sid=twilio_call_sid,
                storage_path=storage_path,
                storage_url=storage_url,
                duration_seconds=duration_seconds,
                file_size_bytes=file_size,
                transcription_text=transcription.get("text", ""),
                transcription_language=transcription.get("language", "en"),
                transcription_confidence=transcription.get("confidence", 0.0),
                key_topics=key_topics,
                sentiment=sentiment,
                recorded_at=recorded_at
            )
            
            logger.info(f"[RECORDING] Recording saved: {recording_record['id']}")
            
            return {
                "status": "success",
                "recording_id": str(recording_record["id"]),
                "storage_path": storage_path,
                "storage_url": storage_url,
                "duration_seconds": duration_seconds,
                "file_size_bytes": file_size,
                "transcription_length": len(transcription.get("text", "")),
                "key_topics": key_topics,
                "sentiment": sentiment
            }
        
        except Exception as e:
            logger.error(f"[RECORDING] Error saving recording: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def _download_recording(self, recording_url: str) -> Optional[bytes]:
        """Download recording from URL"""
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                # Add Twilio auth if needed
                response = await client.get(recording_url, timeout=60.0)
                if response.status_code == 200:
                    return response.content
                else:
                    logger.error(f"Failed to download: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Error downloading recording: {e}")
            return None
    
    async def _transcribe_recording(self, audio_bytes: bytes) -> Dict[str, Any]:
        """Transcribe audio using Whisper"""
        try:
            logger.info("[RECORDING] Calling Whisper transcription")
            
            # Whisper service transcribes from URL or file
            # We'll pass the bytes, Whisper will handle it
            result = self.whisper_service.transcribe_from_bytes(audio_bytes)
            
            return {
                "text": result.get("text", ""),
                "language": result.get("language", "en"),
                "confidence": result.get("confidence", 0.0)
            }
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return {"text": "", "language": "en", "confidence": 0.0}
    
    def _extract_topics(self, text: str) -> list:
        """Extract key topics from transcription"""
        try:
            if not text:
                return []
            
            text_lower = text.lower()
            topics = []
            
            # Simple keyword extraction
            topic_keywords = {
                "pricing": ["price", "cost", "fee", "charge", "payment", "rate"],
                "product": ["product", "feature", "service", "solution", "tool", "platform"],
                "demo": ["demo", "trial", "test", "show", "see", "example"],
                "timeline": ["when", "time", "date", "schedule", "implement", "launch"],
                "comparison": ["vs", "alternative", "competitor", "instead", "rather"],
                "objection": ["but", "however", "concern", "issue", "problem", "worry"],
                "conversion": ["yes", "interested", "sounds good", "let's", "agree", "deal"],
            }
            
            for topic, keywords in topic_keywords.items():
                if any(kw in text_lower for kw in keywords):
                    topics.append(topic)
            
            return topics[:5]  # Return top 5
        except Exception as e:
            logger.error(f"Topic extraction error: {e}")
            return []
    
    def _analyze_sentiment(self, text: str) -> str:
        """Analyze sentiment from transcription"""
        try:
            if not text:
                return "neutral"
            
            text_lower = text.lower()
            
            positive_words = ["great", "excellent", "good", "love", "perfect", "amazing", "wonderful", "fantastic", "thanks"]
            negative_words = ["bad", "terrible", "hate", "worst", "awful", "issue", "problem", "concern", "worry", "unfortunately"]
            
            pos_count = sum(1 for word in positive_words if word in text_lower)
            neg_count = sum(1 for word in negative_words if word in text_lower)
            
            if pos_count > neg_count:
                return "positive"
            elif neg_count > pos_count:
                return "negative"
            else:
                return "neutral"
        except Exception as e:
            logger.error(f"Sentiment analysis error: {e}")
            return "neutral"
    
    async def get_recording_details(self, recording_id: UUID) -> Dict[str, Any]:
        """Get full recording details"""
        try:
            await self._ensure_initialized()
            query = "SELECT * FROM call_recordings WHERE id = $1"
            result = await self.repository.db.execute_fetchone(query, (str(recording_id),))
            
            if not result:
                return {"error": "Recording not found"}
            
            return {
                "id": str(result["id"]),
                "call_session_id": str(result["call_session_id"]),
                "storage_path": result["storage_path"],
                "storage_url": result["storage_url"],
                "duration_seconds": result["duration_seconds"],
                "file_size_bytes": result["file_size_bytes"],
                "transcription": result["transcription_text"][:500] + "..." if result.get("transcription_text") else "",
                "language": result["transcription_language"],
                "key_topics": result.get("key_topics", []),
                "sentiment": result["sentiment"],
                "recorded_at": str(result["recorded_at"]),
                "created_at": str(result["created_at"])
            }
        except Exception as e:
            logger.error(f"Error fetching recording: {e}")
            return {"error": str(e)}
    
    async def search_recordings_by_transcript(
        self,
        query_text: str,
        limit: int = 10
    ) -> list:
        """Search recordings by transcript text"""
        try:
            await self._ensure_initialized()
            
            # Simple full-text search in transcriptions
            search_query = f"%{query_text}%"
            sql = """
            SELECT id, call_session_id, duration_seconds, transcription_text, sentiment, created_at
            FROM call_recordings
            WHERE transcription_text ILIKE $1
            ORDER BY created_at DESC
            LIMIT $2
            """
            
            results = await self.repository.db.execute_query(sql, (search_query, limit))
            
            return [
                {
                    "recording_id": str(r["id"]),
                    "call_session_id": str(r["call_session_id"]),
                    "duration": r["duration_seconds"],
                    "sentiment": r["sentiment"],
                    "created_at": str(r["created_at"]),
                    "excerpt": r["transcription_text"][:150] + "..." if r.get("transcription_text") else ""
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []


# Global instance
_recording_service: Optional[CallRecordingService] = None


async def get_recording_service() -> CallRecordingService:
    """Get or create recording service"""
    global _recording_service
    if _recording_service is None:
        _recording_service = CallRecordingService()
    return _recording_service
