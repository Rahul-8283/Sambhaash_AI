"""
Shared fixtures.

The suite never touches the network, Supabase, Redis, Twilio or Groq: everything
external is replaced by the fakes below. Run it from Backend/ with `pytest`.
"""

import json
import uuid
from datetime import datetime, timezone

import pytest


class FakeRepository:
    """In-memory stand-in for services.database.repository.Repository."""

    def __init__(self, history=None):
        self.history = json.dumps(history or [])
        self.writes = []
        self.created_lead = False

    async def get_call_session(self, session_id):
        return {
            "id": session_id,
            "conversation_history": self.history,
            "created_at": datetime.now(timezone.utc),
        }

    async def update_call_session(self, session_id, **fields):
        if "conversation_history" in fields:
            self.history = json.dumps(fields["conversation_history"])
        self.writes.append(("session", {k: v for k, v in fields.items() if k != "conversation_history"}))

    async def create_lead(self, **kwargs):
        self.created_lead = True
        return {"id": uuid.uuid4()}

    async def create_call_session(self, **kwargs):
        self.created_lead = True
        return {"id": uuid.uuid4()}

    async def create_lead_score(self, **fields):
        self.writes.append(("score", fields))
        return {"id": 1}

    async def update_lead(self, **fields):
        self.writes.append(("lead", fields))

    async def assign_lead_to_rm(self, *args):
        self.writes.append(("rm", args))

    async def get_lead(self, lead_id):
        return {"phone": "+910000000000", "language": "en"}

    def written(self, kind):
        return [fields for k, fields in self.writes if k == kind]


class FakeQueue:
    def __init__(self, sink):
        self.sink = sink

    async def enqueue_job(self, job_type, payload):
        self.sink.append((job_type, payload))


@pytest.fixture
def repo():
    return FakeRepository()


def turns(*pairs, language="en"):
    """Stored-history helper: turns(("hi", "hello")) -> [{"user", "ai", ...}]."""
    return [{"user": u, "ai": a, "language": language, "timestamp": "t"} for u, a in pairs]
