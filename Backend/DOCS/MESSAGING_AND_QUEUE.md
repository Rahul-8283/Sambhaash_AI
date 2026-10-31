# Messaging and the job queue

## Queue — `worker/queue_manager.py`

Redis sorted sets, one per job type, drained with atomic `ZPOPMIN`. Job state is
`pending → processing → completed | failed`. Failures retry with backoff
(1 s, 2 s, 4 s) and then move to the dead-letter queue.

| Job type | Producer | Handler |
|---|---|---|
| `send_whatsapp` | scoring (WARM) | `_process_send_whatsapp`: `warm_follow_up`, `conversion`, `custom` |
| `send_summary` | scoring (every call) | `_process_send_summary`: LLM summary, stored and sent |

Only these two job types exist. `assign_rm`, `update_score` and `process_recording`
were removed because nothing enqueued them (the last had no handler, so its jobs
would have been marked complete without doing anything).

Enqueue from code:

```python
from worker.queue_manager import QueueManager, JobType

await QueueManager().enqueue_job(
    JobType.SEND_WHATSAPP.value,
    {"lead_id": str(lead_id), "message_type": "warm_follow_up", "language": "ta"},
)
```

Operations: `GET /api/queue/stats`, `GET /api/queue/dlq`,
`POST /api/queue/dlq/{job_id}/retry`. Running several workers is safe (each job
is delivered once), but `run_worker.py` takes no `--workers` flag.

## WhatsApp — `services/messaging/whatsapp_service.py`

Templates are plain text keyed `<type>_<language-code>`.

| Template | Languages |
|---|---|
| `warm_follow_up` | en, hi, mr, bn, gu, pa, or, ta, te, kn, ml |
| `conversion` | en, hi (other languages fall back to English) |

The non-English/Hindi follow-ups are machine translations and need a native
speaker's review. The follow-up thanks the lead for talking about the Rupeezy
Partner Program and says the team will share details; it makes no offer, price
or link claims. `conversion` is a partner welcome, not a loan approval.

Language comes from the lead record, which is updated from the language spoken
on the call. Numbers are normalized to E.164 (`utils/phone.py`) at upload.

### Twilio setup

- Sandbox sender: `TWILIO_WHATSAPP_FROM=whatsapp:+14155238886`; each recipient
  must first message the sandbox join code.
- Sandbox "When a message comes in": `{base}/api/webhook/whatsapp` (the LLM reply
  handler). The old canned `/api/webhook/twilio/whatsapp` route no longer exists.
- A follow-up that fails after every retry parks the lead as `FOLLOW_UP` instead of
  only landing in the dead-letter queue.
- Outside the sandbox, business-initiated messages need approved templates
  (content SIDs); free-form text is only allowed inside a user-initiated window.
- Trial accounts can only message verified numbers.

Inbound replies from WARM/HOT leads get a short LLM answer in the lead's
language via `llm_client.generate`.
