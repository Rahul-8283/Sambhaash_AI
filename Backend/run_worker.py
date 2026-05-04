#!/usr/bin/env python3
"""
Background Worker Entrypoint

Runs both the Call Initiator (finds NEW leads and calls them)
and the Job Queue Worker (processes async jobs like WhatsApp sends).

Run this as a separate process/service:
    python run_worker.py

Or in production:
    nohup python run_worker.py > worker.log 2>&1 &
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add Backend directory to path
sys.path.insert(0, str(Path(__file__).parent))

from worker.call_worker import BackgroundWorker
from worker.call_initiator import CallInitiator


def setup_logging():
    """Setup logging configuration."""
    import os
    
    # Force UTF-8 encoding for Windows
    if sys.platform.startswith('win'):
        os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("worker.log", encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Reconfigure stdout for UTF-8 on Windows
    if sys.platform.startswith('win'):
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


async def main():
    """Main entry point."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 80)
    logger.info("[WORKER] Sambhaash AI Background Worker (Call Initiator + Job Processor)")
    logger.info("[WORKER] Note: Ngrok tunnel is managed by backend (Terminal 1)")
    logger.info("=" * 80)
    
    # Create both worker instances
    call_initiator = CallInitiator()
    job_worker = BackgroundWorker()
    
    try:
        # Run both workers concurrently
        # call_initiator: Finds NEW leads every 30s and initiates calls
        # job_worker: Processes async jobs (WhatsApp, scoring, RM assignment)
        await asyncio.gather(
            call_initiator.start_scheduler(poll_interval=30),
            job_worker.start_polling(poll_interval=5, max_workers=3),
            return_exceptions=True
        )
    except KeyboardInterrupt:
        logger.info("[WORKER] Workers stopped by user")
    except Exception as e:
        logger.error(f"[WORKER] Worker crashed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
