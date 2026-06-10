from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import logging

from worker.queue_manager import QueueManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/queue", tags=["queue"])

def get_queue_manager() -> QueueManager:
    return QueueManager()

@router.get("/stats", response_model=Dict[str, Any])
async def get_queue_stats():
    """Get statistics about the queue and workers"""
    try:
        manager = get_queue_manager()
        stats = await manager.get_queue_stats()
        return stats
    except Exception as e:
        logger.error(f"[QUEUE] Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dlq", response_model=List[Dict[str, Any]])
async def get_dlq_jobs(limit: int = 50):
    """Get jobs currently in the Dead Letter Queue"""
    try:
        manager = get_queue_manager()
        jobs = await manager.get_dlq_jobs(limit=limit)
        return jobs
    except Exception as e:
        logger.error(f"[QUEUE] Error getting DLQ jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/dlq/{job_id}/retry", response_model=Dict[str, Any])
async def retry_dlq_job(job_id: str):
    """Move a job from the DLQ back to the main queue for retry"""
    try:
        manager = get_queue_manager()
        success = await manager.retry_dlq_job(job_id)
        if success:
            return {"success": True, "message": f"Job {job_id} re-queued successfully"}
        else:
            raise HTTPException(status_code=404, detail="Job not found in DLQ or could not be retried")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[QUEUE] Error retrying DLQ job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
