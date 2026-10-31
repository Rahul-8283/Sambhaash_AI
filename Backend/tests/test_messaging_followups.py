import asyncio

from api.routes.whatsapp_routes import whatsapp_system_prompt
from services.messaging.whatsapp_service import WhatsAppService
from worker.call_worker import BackgroundWorker
from worker.queue_manager import JobType


def test_inbound_whatsapp_prompt_pitches_partner_program_not_a_loan():
    prompt = whatsapp_system_prompt("Asha", "hi")
    assert "Partner Program" in prompt and "Asha" in prompt and "(hi)" in prompt
    assert "loan" not in prompt.lower() and "₹" not in prompt and "0%" not in prompt


class _Repo:
    def __init__(self):
        self.updates = []

    async def update_lead(self, **fields):
        self.updates.append(fields)


def _worker():
    w = BackgroundWorker.__new__(BackgroundWorker)
    w.repository = _Repo()
    return w


def test_undeliverable_whatsapp_parks_the_lead_for_follow_up():
    w = _worker()
    job = {"payload": {"lead_id": "11111111-1111-1111-1111-111111111111", "message_type": "warm_follow_up"}}
    asyncio.run(w._on_job_exhausted(JobType.SEND_WHATSAPP, job))
    assert w.repository.updates and w.repository.updates[0]["status"] == "FOLLOW_UP"


def test_failed_rm_notification_or_summary_does_not_touch_the_lead():
    w = _worker()
    rm = {"payload": {"lead_id": "11111111-1111-1111-1111-111111111111", "message_type": "rm_notification"}}
    asyncio.run(w._on_job_exhausted(JobType.SEND_WHATSAPP, rm))
    asyncio.run(w._on_job_exhausted(JobType.SEND_SUMMARY, {"payload": {"lead_id": "x"}}))
    assert w.repository.updates == []


def test_whatsapp_sender_normalizes_instead_of_assuming_india():
    sent = {}

    class _Msgs:
        def create(self, **kw):
            sent.update(kw)
            return type("M", (), {"sid": "SM1", "status": "queued"})()

    svc = WhatsAppService.__new__(WhatsAppService)
    svc.twilio_client = type("C", (), {"messages": _Msgs()})()
    svc.whatsapp_from = "whatsapp:+14155238886"
    asyncio.run(svc._send_via_twilio("7989683240", "hi"))
    assert sent["to"] == "whatsapp:+917989683240"
    asyncio.run(svc._send_via_twilio("+442071234567", "hi"))
    assert sent["to"] == "whatsapp:+442071234567"
