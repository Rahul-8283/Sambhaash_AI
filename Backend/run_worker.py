#!/usr/bin/env python3
"""
Background Worker Entrypoint

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

from backend.worker.call_worker import BackgroundWorker


def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("worker.log"),
            logging.StreamHandler()
        ]
    )


async def main():
    """Main entry point."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 60)
    logger.info("🚀 Sambhaash AI Background Worker")
    logger.info("=" * 60)
    
    worker = BackgroundWorker()
    
    try:
        # Start worker with configuration
        # poll_interval: seconds between queue polls
        # max_workers: concurrent workers per job type
        await worker.start_polling(
            poll_interval=5,
            max_workers=3
        )
    except KeyboardInterrupt:
        logger.info("\n⏹️  Worker stopped by user")
    except Exception as e:
        logger.error(f"❌ Worker crashed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
