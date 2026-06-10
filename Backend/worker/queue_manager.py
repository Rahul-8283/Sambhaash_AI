"""
Redis Queue Manager - Manages background job queuing

Job Types:
- send_whatsapp: Send WhatsApp message to WARM lead
- send_summary: Generate and send call summary
- assign_rm: Assign lead to RM
- update_lead_score: Recalculate lead score

Uses Redis with job status tracking.
"""

import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from uuid import uuid4
from enum import Enum

import redis
from config import get_config

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Job status states."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class JobType(Enum):
    """Job type classifications."""
    SEND_WHATSAPP = "send_whatsapp"
    SEND_SUMMARY = "send_summary"
    ASSIGN_RM = "assign_rm"
    UPDATE_SCORE = "update_score"
    PROCESS_RECORDING = "process_recording"


class QueueManager:
    """
    Manages Redis-based job queue for background tasks.
    
    Features:
    - Job enqueueing with priorities
    - Status tracking (pending → processing → completed/failed)
    - Retry logic with exponential backoff
    - Dead-letter queue for failed jobs
    - Job history and analytics
    """

    def __init__(self):
        """Initialize Redis connection."""
        self.config = get_config()
        self.redis_client = redis.from_url(
            self.config.redis_url or "redis://localhost:6379",
            decode_responses=True,
            max_connections=self.config.redis_max_connections or 50
        )
        
        self.queue_prefix = "queue:"
        self.job_prefix = "job:"
        self.dlq_prefix = "dlq:"  # Dead Letter Queue
        self.history_prefix = "history:"
        
        logger.info("Queue Manager initialized")

    async def enqueue_job(
        self,
        job_type: str,
        payload: Dict[str, Any],
        priority: int = 0,
        max_retries: int = 3,
        delay_seconds: int = 0
    ) -> str:
        """
        Enqueue a background job.
        
        Args:
            job_type: Type of job (send_whatsapp, send_summary, etc)
            payload: Job data/parameters
            priority: Priority (higher = executed first)
            max_retries: Max retry attempts
            delay_seconds: Delay before processing (0 = immediate)
            
        Returns:
            str: Job ID
        """
        job_id = str(uuid4())
        
        job = {
            "id": job_id,
            "type": job_type,
            "payload": payload,
            "status": JobStatus.PENDING.value,
            "priority": priority,
            "max_retries": max_retries,
            "retries": 0,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "delay_until": (datetime.utcnow() + timedelta(seconds=delay_seconds)).isoformat() if delay_seconds > 0 else None,
            "errors": []
        }
        
        # Store job details
        job_key = f"{self.job_prefix}{job_id}"
        self.redis_client.set(
            job_key,
            json.dumps(job),
            ex=86400 * 7  # Expire after 7 days
        )
        
        # Add to queue (sorted by priority, then creation time)
        queue_key = f"{self.queue_prefix}{job_type}"
        self.redis_client.zadd(
            queue_key,
            {job_id: -priority}  # Negative for reverse sort
        )
        
        logger.info(f"✅ Enqueued job: {job_id} (type: {job_type}, priority: {priority})")
        
        return job_id

    async def dequeue_job(self, job_type: str) -> Optional[Dict[str, Any]]:
        """
        Dequeue next job from queue.
        
        Args:
            job_type: Type of job to dequeue
            
        Returns:
            Job dict or None if queue empty
        """
        queue_key = f"{self.queue_prefix}{job_type}"
        
        # Get oldest job (lowest score)
        jobs = self.redis_client.zrange(queue_key, 0, 0)
        if not jobs:
            return None
        
        job_id = jobs[0]
        
        # Fetch job details
        job_key = f"{self.job_prefix}{job_id}"
        job_data = self.redis_client.get(job_key)
        if not job_data:
            # Job expired, remove from queue
            self.redis_client.zrem(queue_key, job_id)
            return None
        
        job = json.loads(job_data)
        
        # Check if delayed
        if job.get("delay_until"):
            delay_until = datetime.fromisoformat(job["delay_until"])
            if datetime.utcnow() < delay_until:
                # Not ready yet, return None
                return None
        
        # Mark as processing
        job["status"] = JobStatus.PROCESSING.value
        job["updated_at"] = datetime.utcnow().isoformat()
        self.redis_client.set(job_key, json.dumps(job), ex=86400 * 7)
        
        # Remove from queue
        self.redis_client.zrem(queue_key, job_id)
        
        logger.info(f"📤 Dequeued job: {job_id}")
        
        return job

    async def mark_job_complete(self, job_id: str) -> bool:
        """
        Mark job as completed.
        
        Args:
            job_id: Job ID
            
        Returns:
            bool: Success status
        """
        try:
            job_key = f"{self.job_prefix}{job_id}"
            job_data = self.redis_client.get(job_key)
            if not job_data:
                logger.warning(f"Job not found: {job_id}")
                return False
            
            job = json.loads(job_data)
            job["status"] = JobStatus.COMPLETED.value
            job["updated_at"] = datetime.utcnow().isoformat()
            
            # Store in history
            history_key = f"{self.history_prefix}completed:{job_id}"
            self.redis_client.set(history_key, json.dumps(job), ex=86400 * 30)
            
            # Update job
            self.redis_client.set(job_key, json.dumps(job), ex=86400 * 7)
            
            logger.info(f"✅ Job completed: {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error marking job complete: {e}")
            return False

    async def mark_job_failed(self, job_id: str, error: str) -> bool:
        """
        Mark job as failed with error message.
        
        Args:
            job_id: Job ID
            error: Error message
            
        Returns:
            bool: Success status (True if retrying, False if DLQ)
        """
        try:
            job_key = f"{self.job_prefix}{job_id}"
            job_data = self.redis_client.get(job_key)
            if not job_data:
                logger.warning(f"Job not found: {job_id}")
                return False
            
            job = json.loads(job_data)
            job["errors"].append({
                "error": error,
                "timestamp": datetime.utcnow().isoformat()
            })
            job["retries"] += 1
            job["updated_at"] = datetime.utcnow().isoformat()
            
            # Check if should retry
            if job["retries"] < job["max_retries"]:
                # Exponential backoff: 1s, 4s, 16s
                delay_seconds = 2 ** (job["retries"] - 1)
                job["status"] = JobStatus.RETRYING.value
                job["delay_until"] = (datetime.utcnow() + timedelta(seconds=delay_seconds)).isoformat()
                
                # Re-add to queue
                queue_key = f"{self.queue_prefix}{job['type']}"
                self.redis_client.zadd(
                    queue_key,
                    {job_id: -job["priority"]}
                )
                
                logger.warning(f"⚠️ Job retrying: {job_id} (attempt {job['retries']}/{job['max_retries']})")
                
            else:
                # Max retries exceeded, move to DLQ
                job["status"] = JobStatus.FAILED.value
                dlq_key = f"{self.dlq_prefix}{job_id}"
                self.redis_client.set(dlq_key, json.dumps(job), ex=86400 * 30)
                
                logger.error(f"❌ Job failed (moved to DLQ): {job_id}")
            
            # Update job
            self.redis_client.set(job_key, json.dumps(job), ex=86400 * 7)
            return job["retries"] < job["max_retries"]
            
        except Exception as e:
            logger.error(f"Error marking job failed: {e}")
            return False

    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current job status.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job dict with status or None if not found
        """
        job_key = f"{self.job_prefix}{job_id}"
        job_data = self.redis_client.get(job_key)
        if not job_data:
            return None
        
        return json.loads(job_data)

    async def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get queue statistics.
        
        Returns:
            Dict with queue metrics
        """
        stats = {
            "timestamp": datetime.utcnow().isoformat(),
            "queues": {},
            "total_pending": 0,
            "dlq_size": 0
        }
        
        # Count jobs in each queue
        for job_type in JobType:
            queue_key = f"{self.queue_prefix}{job_type.value}"
            count = self.redis_client.zcard(queue_key)
            stats["queues"][job_type.value] = count
            stats["total_pending"] += count
        
        # Count DLQ jobs
        dlq_pattern = f"{self.dlq_prefix}*"
        dlq_keys = self.redis_client.keys(dlq_pattern)
        stats["dlq_size"] = len(dlq_keys)
        
        logger.info(f"Queue stats: {stats['total_pending']} pending, {stats['dlq_size']} DLQ")
        
        return stats

    async def get_dlq_jobs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get jobs from dead-letter queue.
        
        Args:
            limit: Max jobs to return
            
        Returns:
            List of failed jobs
        """
        dlq_pattern = f"{self.dlq_prefix}*"
        dlq_keys = self.redis_client.keys(dlq_pattern)[:limit]
        
        jobs = []
        for key in dlq_keys:
            job_data = self.redis_client.get(key)
            if job_data:
                jobs.append(json.loads(job_data))
        
        return jobs

    async def retry_dlq_job(self, job_id: str) -> bool:
        """
        Retry a job from dead-letter queue.
        
        Args:
            job_id: Job ID to retry
            
        Returns:
            bool: Success status
        """
        try:
            dlq_key = f"{self.dlq_prefix}{job_id}"
            job_data = self.redis_client.get(dlq_key)
            if not job_data:
                logger.warning(f"DLQ job not found: {job_id}")
                return False
            
            job = json.loads(job_data)
            
            # Reset job for retry
            job["status"] = JobStatus.PENDING.value
            job["retries"] = 0
            job["errors"] = []
            job["updated_at"] = datetime.utcnow().isoformat()
            
            # Re-add to queue
            queue_key = f"{self.queue_prefix}{job['type']}"
            self.redis_client.zadd(
                queue_key,
                {job_id: -job["priority"]}
            )
            
            # Update job
            job_key = f"{self.job_prefix}{job_id}"
            self.redis_client.set(job_key, json.dumps(job), ex=86400 * 7)
            
            # Remove from DLQ
            self.redis_client.delete(dlq_key)
            
            logger.info(f"🔄 DLQ job retried: {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error retrying DLQ job: {e}")
            return False

    async def clear_queue(self, job_type: str) -> int:
        """
        Clear all jobs from a queue.
        
        Args:
            job_type: Type of jobs to clear
            
        Returns:
            int: Number of jobs cleared
        """
        queue_key = f"{self.queue_prefix}{job_type}"
        count = self.redis_client.zcard(queue_key)
        self.redis_client.delete(queue_key)
        
        logger.warning(f"Cleared {count} jobs from {job_type} queue")
        return count
