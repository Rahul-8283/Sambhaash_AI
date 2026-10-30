import asyncio
from datetime import datetime, timezone

from worker.call_initiator import CallInitiator


def _initiator(enabled=True, start=9, end=21):
    ci = CallInitiator.__new__(CallInitiator)

    class Cfg:
        nurture_enabled = enabled
        nurture_max_attempts = 3
        nurture_cooldown_hours = 72
        call_window_start_hour = start
        call_window_end_hour = end

    ci.config = Cfg
    return ci


def test_call_window_uses_india_time():
    ci = _initiator()
    # 04:00 UTC = 09:30 IST (open); 16:00 UTC = 21:30 IST (closed); 20:00 UTC = 01:30 IST (closed)
    assert ci._within_call_window(datetime(2026, 1, 5, 4, 0, tzinfo=timezone.utc))
    assert not ci._within_call_window(datetime(2026, 1, 5, 16, 0, tzinfo=timezone.utc))
    assert not ci._within_call_window(datetime(2026, 1, 5, 20, 0, tzinfo=timezone.utc))


class _Repo:
    def __init__(self):
        self.asked = False

    async def list_nurture_candidates(self, **kw):
        self.asked = True
        return []


def test_nurture_does_nothing_when_disabled():
    ci = _initiator(enabled=False)
    ci.repository = _Repo()
    asyncio.run(ci.find_and_call_nurture_leads())
    assert not ci.repository.asked


def test_nurture_skips_outside_call_window():
    ci = _initiator(start=0, end=0)  # never inside the window
    ci.repository = _Repo()
    asyncio.run(ci.find_and_call_nurture_leads())
    assert not ci.repository.asked


def test_nurture_queries_inside_window():
    ci = _initiator(start=0, end=24)
    ci.repository = _Repo()
    asyncio.run(ci.find_and_call_nurture_leads())
    assert ci.repository.asked
