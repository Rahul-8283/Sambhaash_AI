"""
Call Recording Admin Routes (Phase 2B)
Endpoints for managing call recordings and transcriptions
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from uuid import UUID
import logging

from services.database.supabase_client import get_db_client, SupabaseClient
from services.database.repository import Repository
from services.call_recording_service import get_recording_service, CallRecordingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/recordings", tags=["admin-recordings"])


# ==================== PYDANTIC MODELS ====================

class RecordingMetadata(BaseModel):
    """Recording metadata"""
    id: str
    call_session_id: str
    duration_seconds: int
    file_size_bytes: int
    storage_path: str
    storage_url: str
    language: str
    sentiment: str
    key_topics: List[str]
    created_at: str


class RecordingDetails(BaseModel):
    """Full recording details"""
    id: str
    call_session_id: str
    duration_seconds: int
    file_size_bytes: int
    storage_url: str
    transcription: Optional[str]
    language: str
    sentiment: str
    key_topics: List[str]
    recorded_at: str
    created_at: str


class RecordingSearchResult(BaseModel):
    """Search result"""
    recording_id: str
    call_session_id: str
    duration_seconds: int
    sentiment: str
    excerpt: str
    created_at: str


class RecordingsListResponse(BaseModel):
    """List recordings response"""
    recordings: List[RecordingMetadata]
    total: int
    page: int
    limit: int


class RecordingStatistics(BaseModel):
    """Recording statistics"""
    total_recordings: int
    avg_duration_seconds: float
    total_storage_bytes: int
    by_sentiment: Dict[str, int]


# ==================== ROUTES ====================


@router.get(
    "/",
    response_model=RecordingsListResponse,
    summary="List all call recordings"
)
async def list_call_recordings(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    language: Optional[str] = Query(None, description="Filter by language"),
    sentiment: Optional[str] = Query(None, description="Filter by sentiment (positive/negative/neutral)"),
    db: SupabaseClient = Depends(get_db_client),
) -> RecordingsListResponse:
    """
    Get list of all call recordings with optional filters.
    
    Filters:
    - language: ISO 639-1 code (en, hi, etc.)
    - sentiment: positive, negative, neutral
    """
    try:
        offset = (page - 1) * limit
        repo = Repository(db)
        
        recordings, total = await repo.list_recordings(
            limit=limit,
            offset=offset,
            language=language,
            sentiment=sentiment
        )
        
        formatted = [
            RecordingMetadata(
                id=str(r["id"]),
                call_session_id=str(r["call_session_id"]),
                duration_seconds=r["duration_seconds"],
                file_size_bytes=r.get("file_size_bytes", 0),
                storage_path=r.get("storage_path", ""),
                storage_url=r.get("storage_url", ""),
                language=r.get("transcription_language", "en"),
                sentiment=r.get("sentiment", "neutral"),
                key_topics=r.get("key_topics", []),
                created_at=str(r["created_at"])
            )
            for r in recordings
        ]
        
        logger.info(f"[RECORDINGS] Listed {len(recordings)} recordings (page {page}, total {total})")
        
        return RecordingsListResponse(
            recordings=formatted,
            total=total,
            page=page,
            limit=limit
        )
    except Exception as e:
        logger.error(f"[RECORDINGS] List error: {e}")
        raise HTTPException(status_code=500, detail="Failed to list recordings")


@router.get(
    "/{recording_id}",
    response_model=RecordingDetails,
    summary="Get recording details"
)
async def get_recording_details(
    recording_id: str,
    db: SupabaseClient = Depends(get_db_client),
) -> RecordingDetails:
    """Get full details of a recording including transcription"""
    try:
        repo = Repository(db)
        recording = await repo.get_call_recording(UUID(recording_id))
        
        if not recording:
            raise HTTPException(status_code=404, detail="Recording not found")
        
        logger.info(f"[RECORDINGS] Retrieved details for {recording_id}")
        
        return RecordingDetails(
            id=str(recording["id"]),
            call_session_id=str(recording["call_session_id"]),
            duration_seconds=recording["duration_seconds"],
            file_size_bytes=recording["file_size_bytes"],
            storage_url=recording["storage_url"],
            transcription=recording.get("transcription_text", "")[:1000],
            language=recording.get("transcription_language", "en"),
            sentiment=recording["sentiment"],
            key_topics=recording.get("key_topics", []),
            recorded_at=str(recording["recorded_at"]),
            created_at=str(recording["created_at"])
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[RECORDINGS] Get details error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get recording")


@router.get(
    "/session/{session_id}",
    response_model=RecordingDetails,
    summary="Get recording for a call session"
)
async def get_session_recording(
    session_id: str,
    db: SupabaseClient = Depends(get_db_client),
) -> RecordingDetails:
    """Get recording associated with a call session"""
    try:
        repo = Repository(db)
        recording = await repo.get_recording_by_session(UUID(session_id))
        
        if not recording:
            raise HTTPException(status_code=404, detail="No recording found for this session")
        
        logger.info(f"[RECORDINGS] Retrieved recording for session {session_id}")
        
        return RecordingDetails(
            id=str(recording["id"]),
            call_session_id=str(recording["call_session_id"]),
            duration_seconds=recording["duration_seconds"],
            file_size_bytes=recording["file_size_bytes"],
            storage_url=recording["storage_url"],
            transcription=recording.get("transcription_text", "")[:1000],
            language=recording.get("transcription_language", "en"),
            sentiment=recording["sentiment"],
            key_topics=recording.get("key_topics", []),
            recorded_at=str(recording["recorded_at"]),
            created_at=str(recording["created_at"])
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[RECORDINGS] Session recording error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get session recording")


@router.get(
    "/search/by-text",
    response_model=List[RecordingSearchResult],
    summary="Search recordings by transcript text"
)
async def search_recordings(
    query: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=50, description="Max results"),
    db: SupabaseClient = Depends(get_db_client),
) -> List[RecordingSearchResult]:
    """
    Search all recordings by transcript text.
    
    Searches in transcription_text field with case-insensitive full-text search.
    """
    try:
        repo = Repository(db)
        results = await repo.search_recordings_by_text(query, limit=limit)
        
        formatted = [
            RecordingSearchResult(
                recording_id=str(r["id"]),
                call_session_id=str(r["call_session_id"]),
                duration_seconds=r["duration_seconds"],
                sentiment=r["sentiment"],
                excerpt=r.get("transcription_text", "")[:150] + "...",
                created_at=str(r["created_at"])
            )
            for r in results
        ]
        
        logger.info(f"[RECORDINGS] Found {len(formatted)} results for query: '{query}'")
        
        return formatted
    except Exception as e:
        logger.error(f"[RECORDINGS] Search error: {e}")
        raise HTTPException(status_code=500, detail="Search failed")


@router.get(
    "/download/{recording_id}",
    summary="Download recording audio file"
)
async def download_recording(
    recording_id: str,
    db: SupabaseClient = Depends(get_db_client),
) -> Dict[str, str]:
    """
    Get direct download URL for a recording.
    
    Returns the public URL from Supabase Storage that can be used to download the audio.
    """
    try:
        repo = Repository(db)
        recording = await repo.get_call_recording(UUID(recording_id))
        
        if not recording:
            raise HTTPException(status_code=404, detail="Recording not found")
        
        storage_url = recording.get("storage_url", "")
        if not storage_url:
            raise HTTPException(status_code=400, detail="Recording URL not available")
        
        logger.info(f"[RECORDINGS] Download link generated for {recording_id}")
        
        return {
            "download_url": storage_url,
            "file_name": recording.get("storage_path", "").split("/")[-1],
            "size_bytes": recording["file_size_bytes"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[RECORDINGS] Download error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get download link")


@router.get(
    "/statistics",
    response_model=RecordingStatistics,
    summary="Get recording statistics"
)
async def get_recording_stats(
    db: SupabaseClient = Depends(get_db_client),
) -> RecordingStatistics:
    """Get aggregate statistics about call recordings"""
    try:
        repo = Repository(db)
        stats = await repo.get_recording_statistics()
        
        # Calculate averages
        total_recordings = stats.get("total_recordings", 0)
        avg_duration = 0.0
        total_storage = 0
        
        # Format sentiment breakdown
        by_sentiment = {}
        for record in stats.get("recordings_by_sentiment", []):
            sentiment = record.get("sentiment", "unknown")
            count = record.get("count", 0)
            by_sentiment[sentiment] = count
        
        logger.info(f"[RECORDINGS] Statistics: {total_recordings} total recordings")
        
        return RecordingStatistics(
            total_recordings=total_recordings,
            avg_duration_seconds=avg_duration,
            total_storage_bytes=total_storage,
            by_sentiment=by_sentiment
        )
    except Exception as e:
        logger.error(f"[RECORDINGS] Stats error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")


@router.get(
    "/transcription/{recording_id}",
    summary="Get full transcription text"
)
async def get_transcription(
    recording_id: str,
    db: SupabaseClient = Depends(get_db_client),
) -> Dict[str, Any]:
    """Get complete transcription text for a recording"""
    try:
        repo = Repository(db)
        recording = await repo.get_call_recording(UUID(recording_id))
        
        if not recording:
            raise HTTPException(status_code=404, detail="Recording not found")
        
        logger.info(f"[RECORDINGS] Retrieved transcription for {recording_id}")
        
        return {
            "recording_id": str(recording["id"]),
            "call_session_id": str(recording["call_session_id"]),
            "transcription": recording.get("transcription_text", ""),
            "language": recording.get("transcription_language", "en"),
            "confidence": recording.get("transcription_confidence", 0.0),
            "duration_seconds": recording["duration_seconds"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[RECORDINGS] Transcription error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get transcription")
