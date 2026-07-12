"""
Background Job Worker - Processes queued jobs

Runs as a separate process/service.

Flow:
1. Poll Redis queue for jobs
2. Process job (send WhatsApp, update score, etc)
3. Mark as complete or failed
4. Move to DLQ if max retries exceeded
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from worker.queue_manager import QueueManager, JobStatus, JobType
from services.messaging.whatsapp_service import WhatsAppService
from services.scoring.scoring_engine import ScoringEngine
from services.database.supabase_client import get_db_client, close_db_client
from services.database.repository import Repository
from services.llm.llm_client import LLMClient
from services.llm.summary_generator import SummaryGenerator
from config import get_config

logger = logging.getLogger(__name__)


class BackgroundWorker:
    """
    Background job worker for processing async tasks.
    
    Handles:
    - WhatsApp message sending
    - Call summary generation
    - Lead scoring updates
    - RM assignments
    """

    def __init__(self):
        """Initialize background worker."""
        self.config = get_config()
        self.queue_manager = QueueManager()
        self.db_client: Optional[Any] = None
        self.repository: Optional[Repository] = None
        self.whatsapp_service: Optional[WhatsAppService] = None
        self.scoring_engine: Optional[ScoringEngine] = None
        
        logger.info("Background Worker initialized")

    async def startup(self):
        """Initialize database and services."""
        try:
            self.db_client = await get_db_client()
            self.repository = Repository(self.db_client)
            self.whatsapp_service = WhatsAppService(self.repository)
            self.scoring_engine = ScoringEngine(self.repository)
            
            logger.info("[WORKER] Worker startup complete")
        except Exception as e:
            logger.error(f"[WORKER] Worker startup failed: {e}")
            raise

    async def shutdown(self):
        """Cleanup on shutdown."""
        try:
            if self.db_client:
                await close_db_client()
            logger.info("Worker shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    async def start_polling(self, poll_interval: int = 5, max_workers: int = 3):
        """
        Start polling job queues and processing jobs.
        
        Args:
            poll_interval: Seconds between polls
            max_workers: Max concurrent workers
        """
        logger.info(f"[WORKER] Starting worker (poll_interval={poll_interval}s, max_workers={max_workers})")
        
        # Safe serial connection retry loop on boot to avoid parallel race conditions
        while not self.repository:
            try:
                await self.startup()
            except Exception as e:
                logger.warning(f"[WORKER] Database connection failed ({e}). Retrying in 3 seconds...")
                await asyncio.sleep(3)
        
        try:
            tasks = [
                asyncio.create_task(self._worker_loop(job_type, poll_interval))
                for job_type in JobType
                for _ in range(max_workers)
            ]
            
            await asyncio.gather(*tasks)
            
        except KeyboardInterrupt:
            logger.info("Worker interrupted by user")
        except Exception as e:
            logger.error(f"Worker error: {e}")
        finally:
            await self.shutdown()

    async def _worker_loop(self, job_type: JobType, poll_interval: int):
        """
        Worker loop for processing specific job type.
        
        Args:
            job_type: Type of jobs to process
            poll_interval: Seconds between polls
        """
        logger.info(f"Worker started for {job_type.value}")
        
        while True:
            # Self-healing database connection check (failsafe)
            if not self.repository:
                try:
                    self.db_client = await get_db_client()
                    self.repository = Repository(self.db_client)
                except Exception as e:
                    logger.warning(f"[WORKER] Connection retry failed for loop {job_type.value}: {e}. Waiting for network...")
                    await asyncio.sleep(poll_interval)
                    continue

            try:
                # Poll for next job
                job = await self.queue_manager.dequeue_job(job_type.value)
                
                if job:
                    logger.info(f"Processing job: {job['id']} ({job_type.value})")
                    
                    try:
                        # Process job based on type
                        if job_type == JobType.SEND_WHATSAPP:
                            await self._process_send_whatsapp(job)
                        elif job_type == JobType.SEND_SUMMARY:
                            await self._process_send_summary(job)
                        elif job_type == JobType.ASSIGN_RM:
                            await self._process_assign_rm(job)
                        elif job_type == JobType.UPDATE_SCORE:
                            await self._process_update_score(job)
                        
                        # Mark as complete
                        await self.queue_manager.mark_job_complete(job["id"])
                        
                    except Exception as e:
                        logger.error(f"Job processing failed: {e}")
                        await self.queue_manager.mark_job_failed(job["id"], str(e))
                
                else:
                    # No jobs, wait before polling again
                    await asyncio.sleep(poll_interval)
                    
            except Exception as e:
                logger.error(f"Worker loop error: {e}")
                await asyncio.sleep(poll_interval)

    async def _process_send_whatsapp(self, job: Dict[str, Any]):
        """
        Process WhatsApp sending job.
        
        Args:
            job: Job dict with payload
        """
        payload = job["payload"]
        lead_id = payload.get("lead_id")
        message_type = payload.get("message_type", "warm_follow_up")
        language = payload.get("language", "hi")
        
        logger.info(f"Sending WhatsApp to lead {lead_id} (type: {message_type})")
        
        if message_type == "warm_follow_up":
            result = await self.whatsapp_service.send_warm_follow_up(lead_id, language)
        elif message_type == "conversion":
            result = await self.whatsapp_service.send_conversion_confirmation(
                lead_id,
                amount=payload.get("amount", 0),
                tenure=payload.get("tenure", 12),
                interest_rate=payload.get("interest_rate", 8.5),
                language=language
            )
        elif message_type == "custom":
            result = await self.whatsapp_service.send_custom_message(
                lead_id,
                message=payload.get("message", "")
            )
        else:
            raise ValueError(f"Unknown message type: {message_type}")
        
        if not result.get("success"):
            raise Exception(f"WhatsApp send failed: {result.get('error')}")
        
        logger.info(f"[WORKER] WhatsApp sent: {result}")

    async def _process_send_summary(self, job: Dict[str, Any]):
        """
        Process call summary generation and sending.
        
        Args:
            job: Job dict with payload
        """
        payload = job["payload"]
        session_id = payload.get("session_id")
        lead_id = payload.get("lead_id")
        
        logger.info(f"Generating summary for session {session_id}")
        
        # Get call session
        session = await self.repository.get_call_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        # Set up LLM Client (using groq mixtral model as default)
        config = get_config()
        llm_client = LLMClient(
            model_name=config.llm_model_name,
            api_key=config.groq_api_key,
            base_url="https://api.groq.com/openai/v1"
        )
        
        # Initialize SummaryGenerator
        summary_generator = SummaryGenerator(llm_client=llm_client)
        
        # Extract required data
        history = session.get("conversation_history", [])
        
        # Generate structured summary
        generated_summary = summary_generator.generate(
            memory_snapshot={"current_classification": session.get("classification")},
            transcript=history
        )
        
        # Save to database
        await self.repository.update_call_session_summary(session_id, generated_summary)
        
        # Format the message for WhatsApp
        objections_text = ", ".join(generated_summary.get("objections_raised", [])) or "None"
        topics_text = ", ".join(generated_summary.get("topics_covered", [])) or "None"
        
        summary_message = f"""*Call Summary*
*Lead ID:* {lead_id}
*Duration:* {session.get('duration_seconds')}s
*Topics Covered:* {topics_text}
*Objections:* {objections_text}
*Action:* {generated_summary.get('recommended_next_action', 'None')}

_{generated_summary.get('one_line_summary', '')}_"""
        
        # Send to lead via WhatsApp
        result = await self.whatsapp_service.send_custom_message(lead_id, summary_message)
        
        if not result.get("success"):
            raise Exception(f"Summary send failed: {result.get('error')}")
        
        logger.info(f"[WORKER] Summary sent for session {session_id}")

    async def _process_assign_rm(self, job: Dict[str, Any]):
        """
        Process RM assignment job.
        
        Args:
            job: Job dict with payload
        """
        payload = job["payload"]
        lead_id = payload.get("lead_id")
        rm_name = payload.get("rm_name", "Auto")
        
        logger.info(f"Assigning lead {lead_id} to RM {rm_name}")
        
        # Assign lead to RM
        result = await self.repository.assign_lead_to_rm(lead_id, rm_name)
        
        logger.info(f"[WORKER] Lead assigned to RM: {result}")

    async def _process_update_score(self, job: Dict[str, Any]):
        """
        Process lead scoring update job.
        
        Args:
            job: Job dict with payload
        """
        payload = job["payload"]
        lead_id = payload.get("lead_id")
        session_id = payload.get("session_id")
        
        logger.info(f"Updating score for lead {lead_id} (session: {session_id})")
        
        # Recalculate score
        result = await self.scoring_engine.recalculate_scores_for_session(session_id, lead_id)
        
        if not result:
            raise ValueError(f"Scoring failed for lead {lead_id}")
        
        logger.info(f"[WORKER] Score updated: {result['classification']}")


async def main():
    """Entry point for background worker."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    worker = BackgroundWorker()
    
    # Start worker with 3 concurrent workers per job type
    await worker.start_polling(poll_interval=5, max_workers=3)


if __name__ == "__main__":
    asyncio.run(main())
