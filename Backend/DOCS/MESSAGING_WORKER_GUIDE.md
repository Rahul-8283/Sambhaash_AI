"""
Messaging & Worker Integration Guide

Shows how to use WhatsApp Service and Job Queue in the application.
"""

# ==================== USAGE EXAMPLES ====================

# Example 1: Queue a WhatsApp message from Scoring Engine
# ======================================================
from backend.worker.queue_manager import QueueManager, JobType
from backend.services.scoring.scoring_engine import ScoringEngine
from backend.services.database.repository import Repository

async def example_scoring_triggers_whatsapp():
    """
    When ScoringEngine detects WARM lead, queue WhatsApp message.
    """
    queue_mgr = QueueManager()
    
    # Example: Lead scored as WARM (0.60 composite score)
    lead_id = "550e8400-e29b-41d4-a716-446655440000"
    
    # Queue warm follow-up message
    job_id = await queue_mgr.enqueue_job(
        job_type=JobType.SEND_WHATSAPP.value,
        payload={
            "lead_id": lead_id,
            "message_type": "warm_follow_up",
            "language": "hi"
        },
        priority=5,  # Medium priority
        max_retries=3,
        delay_seconds=0  # Send immediately
    )
    
    print(f"✅ Enqueued WhatsApp job: {job_id}")


# Example 2: Queue multiple messages for RM assignment
# ====================================================
async def example_hot_lead_triggers_rm_assignment():
    """
    When ScoringEngine detects HOT lead:
    1. Assign to RM
    2. Queue notification message
    """
    queue_mgr = QueueManager()
    repository = Repository(db_client)
    
    lead_id = "550e8400-e29b-41d4-a716-446655440000"
    rm_name = "Rajesh Kumar"
    
    # 1. Assign to RM (synchronous)
    assignment = await repository.assign_lead_to_rm(lead_id, rm_name)
    
    # 2. Queue RM notification message
    job_id = await queue_mgr.enqueue_job(
        job_type=JobType.SEND_WHATSAPP.value,
        payload={
            "lead_id": lead_id,
            "message_type": "hot_reminder",
            "language": "hi",
            "rm_name": rm_name,
            "rm_phone": "+91-9876543210"
        },
        priority=8,  # High priority
        max_retries=2
    )
    
    print(f"✅ RM assigned + notification queued: {job_id}")


# Example 3: Send conversion confirmation
# ========================================
async def example_conversion_message():
    """
    When RM marks lead as converted, send celebration message.
    """
    queue_mgr = QueueManager()
    
    lead_id = "550e8400-e29b-41d4-a716-446655440000"
    
    job_id = await queue_mgr.enqueue_job(
        job_type=JobType.SEND_WHATSAPP.value,
        payload={
            "lead_id": lead_id,
            "message_type": "conversion",
            "language": "hi",
            "amount": 50000,
            "tenure": 12,
            "interest_rate": 8.5
        },
        priority=9,  # Highest priority
        max_retries=3
    )
    
    print(f"✅ Conversion message queued: {job_id}")


# Example 4: Send bulk messages with delay
# =========================================
async def example_bulk_messaging():
    """
    Send messages to multiple WARM leads with delays to avoid API rate limits.
    """
    queue_mgr = QueueManager()
    repository = Repository(db_client)
    
    # Get all WARM leads
    warm_leads = await repository.list_scores_by_classification("WARM")
    
    for idx, lead in enumerate(warm_leads):
        # Stagger messages - 10 second delay between each
        delay = idx * 10
        
        job_id = await queue_mgr.enqueue_job(
            job_type=JobType.SEND_WHATSAPP.value,
            payload={
                "lead_id": lead["lead_id"],
                "message_type": "warm_follow_up",
                "language": lead.get("language", "hi")
            },
            priority=3,
            max_retries=3,
            delay_seconds=delay
        )
    
    print(f"✅ {len(warm_leads)} messages queued with staggered delays")


# Example 5: Monitor queue status
# ===============================
async def example_monitor_queues():
    """
    Check queue health and metrics.
    """
    queue_mgr = QueueManager()
    
    # Get overall stats
    stats = await queue_mgr.get_queue_stats()
    print(f"""
    Queue Stats:
    - Total pending: {stats['total_pending']}
    - WhatsApp queue: {stats['queues'].get('send_whatsapp', 0)}
    - Summary queue: {stats['queues'].get('send_summary', 0)}
    - RM assign queue: {stats['queues'].get('assign_rm', 0)}
    - DLQ (dead-letter): {stats['dlq_size']}
    """)
    
    # Get failed jobs
    dlq_jobs = await queue_mgr.get_dlq_jobs(limit=5)
    if dlq_jobs:
        print("\n❌ Failed jobs (Dead-Letter Queue):")
        for job in dlq_jobs:
            print(f"  - {job['id']}: {job['type']} (retries: {job['retries']})")


# Example 6: Retry failed job
# ===========================
async def example_retry_failed_job():
    """
    Retry a job that failed and was moved to DLQ.
    """
    queue_mgr = QueueManager()
    
    job_id = "failed-job-id-here"
    
    success = await queue_mgr.retry_dlq_job(job_id)
    if success:
        print(f"✅ Job {job_id} moved back to queue for retry")
    else:
        print(f"❌ Failed to retry job {job_id}")


# ==================== RUNNING THE WORKER ====================

# Option 1: Run as standalone process
# ===================================
"""
In terminal:
    cd Backend
    python run_worker.py

This will:
- Poll Redis queues every 5 seconds
- Process up to 3 jobs concurrently per job type
- Retry failed jobs with exponential backoff
- Log all activity to worker.log
"""

# Option 2: Run in production (systemd)
# =====================================
"""
Create /etc/systemd/system/sambhaash-worker.service:

[Unit]
Description=Sambhaash AI Background Worker
After=redis.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/Sambhaash_AI/Backend
ExecStart=/usr/bin/python3 /home/ubuntu/Sambhaash_AI/Backend/run_worker.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

Commands:
    sudo systemctl start sambhaash-worker
    sudo systemctl stop sambhaash-worker
    sudo systemctl status sambhaash-worker
    sudo journalctl -u sambhaash-worker -f  # View logs
"""

# Option 3: Run multiple workers (load balancing)
# ================================================
"""
For high-volume deployments, run multiple worker instances:

worker1$ python run_worker.py --workers=5
worker2$ python run_worker.py --workers=5
worker3$ python run_worker.py --workers=5

Each instance will:
- Poll Redis independently
- Process different jobs
- Share state via Redis

Total capacity: 15 concurrent jobs
"""


# ==================== INTEGRATION WORKFLOW ====================

"""
Complete flow:

1. Call Session Completes
   └─> Person 2 (LLM) saves CallSession with conversation_history

2. Scoring Engine Runs
   └─> Calculates composite_score
   └─> Classification: HOT/WARM/COLD

3. Classification Actions:
   
   a) If HOT (≥0.75):
      ├─> Queue: ASSIGN_RM job
      ├─> Queue: RM notification WhatsApp
      └─> RM sees in queue: GET /api/rm/{name}/queue
   
   b) If WARM (0.50-0.74):
      ├─> Queue: SEND_WHATSAPP job
      └─> Lead receives message in WhatsApp
   
   c) If COLD (<0.50):
      └─> Archive for future campaigns

4. Worker Processes Queue
   ├─> Poll Redis every 5 seconds
   ├─> Dequeue job
   ├─> Execute job (send WhatsApp, assign RM, etc)
   ├─> Mark complete or retry
   └─> Log result

5. RM Marks Converted
   └─> POST /api/rm/{name}/{lead_id}/complete
   └─> Queue: SEND_WHATSAPP conversion confirmation
   └─> Lead receives celebration message

6. Analytics & Monitoring
   └─> GET /api/rm/leaderboard (manager view)
   └─> Dashboard shows conversion rates
"""

print("""
✅ Messaging & Worker Integration Ready!

Key Components:
- WhatsAppService: Send messages via Twilio
- QueueManager: Manage Redis job queue
- BackgroundWorker: Process queued jobs

Run the worker:
    python run_worker.py

Monitor queue:
    python -c "from backend.worker.queue_manager import QueueManager; 
               import asyncio;
               async def main():
                   q = QueueManager()
                   stats = await q.get_queue_stats()
                   print(stats)
               asyncio.run(main())"

Integration:
- Scoring Engine → Queues jobs
- Worker → Processes jobs
- API → RM management endpoints
""")
