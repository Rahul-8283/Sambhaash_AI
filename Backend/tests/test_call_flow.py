"""
A whole call through the real recording webhook, LangGraph and scoring, with the
database, queue, STT, TTS, KB and LLM replaced by fakes.
"""

import asyncio
import json
import re
import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

import main
import orchestration.nodes as nodes
from api.routes import webhook_routes as w
from api.twilio_auth import verify_twilio_signature
from services.scoring.scoring_engine import ScoringEngine
from tests.conftest import FakeQueue, FakeRepository, turns


class FakeLLM:
    """Echoes the language instruction it was given, so tests can assert on it."""

    def __init__(self):
        self.calls = []

    async def ainvoke(self, messages):
        self.calls.append(messages)
        return AIMessage(content="Sure. Would you like the details?")


class FakeSTT:
    def __init__(self, utterances):
        self.utterances = iter(utterances)
        self.hints = []

    def transcribe_recording_url(self, **kwargs):
        self.hints.append(kwargs.get("language"))
        return next(self.utterances)


class FakeKB:
    def __init__(self, *args, **kwargs):
        pass

    async def retrieve_context_for_call(self, **kwargs):
        return {"context_blocks": [], "formatted_context": "", "kb_available": False}


@pytest.fixture
def call(monkeypatch):
    """Returns (client, repo, stt, queue_jobs, spoken) wired with fakes."""
    repo = FakeRepository()
    jobs, spoken = [], []
    llm = FakeLLM()

    async def fake_db():
        return object()

    class FakeTTS:
        async def generate_tts(self, text, language):
            spoken.append((text, language))
            return b"RIFFfake"

        async def start_tts(self, text, language):
            # mirrors the real contract: first chunk's bytes plus tasks for the rest
            return await self.generate_tts(text, language), []

    monkeypatch.setattr(nodes, "llm", llm)
    monkeypatch.setattr(w, "get_db_client", fake_db)
    monkeypatch.setattr(w, "Repository", lambda db: repo)
    monkeypatch.setattr(w, "QueueManager", lambda: FakeQueue(jobs))
    monkeypatch.setattr(w, "KBContextInjectionService", FakeKB)
    monkeypatch.setattr(w, "_call_manager", FakeTTS())
    monkeypatch.setattr(w, "_language_detector", None)
    monkeypatch.setattr(w, "_stt_service", None)
    main.app.dependency_overrides[verify_twilio_signature] = lambda: None

    def build(utterances):
        stt = FakeSTT(utterances)
        monkeypatch.setattr(w, "_stt_service", stt)
        return TestClient(main.app, base_url="http://localhost"), repo, stt, jobs, spoken

    yield build
    main.app.dependency_overrides.pop(verify_twilio_signature, None)


def _post_turn(client, query, call_sid="CA-test"):
    response = client.post(
        "/api/webhook/twilio/recording" + query,
        data={"CallSid": call_sid, "From": "+910000000000", "RecordingUrl": "http://rec/x", "RecordingDuration": "5"},
    )
    assert response.status_code == 200
    return response.text


def _next_query(twiml):
    match = re.search(r'<Record action="([^"]+)"', twiml)
    return ("?" + match.group(1).replace("&amp;", "&").split("?", 1)[1]) if match else None


def test_three_turn_call_remembers_scores_hot_and_hands_to_rm(call):
    client, repo, stt, jobs, spoken = call([
        "Hi, tell me about the partner program and how I earn commission?",
        "What documents do I need to join?",
        "Yes I am interested, please call me back",
    ])
    session_id, lead_id = str(uuid.uuid4()), str(uuid.uuid4())
    query = f"?session_id={session_id}&lead_id={lead_id}"

    first = _post_turn(client, query)
    query = _next_query(first)
    # The session must travel in the next-turn URL, not only in process memory
    assert query and f"session_id={session_id}" in query and f"lead_id={lead_id}" in query

    second = _post_turn(client, query)
    query = _next_query(second)
    final = _post_turn(client, query)

    assert "Hangup" in final and _next_query(final) is None
    history = json.loads(repo.history)
    assert [t["user"] for t in history][0].startswith("Hi, tell me")
    assert len(history) == 3
    assert not repo.created_lead, "a bogus lead/session was created mid-call"

    scores = repo.written("score")
    assert len(scores) == 1 and scores[0]["classification"] == "HOT"
    assert repo.written("rm"), "HOT lead should be assigned to an RM"
    assert [t for t, _ in jobs] == ["send_summary"]
    assert any(f.get("status") == "INTERESTED" for f in repo.written("lead"))


def test_model_receives_earlier_turns(call):
    client, repo, stt, jobs, spoken = call(["first question about commission", "and second question about documents"])
    query = f"?session_id={uuid.uuid4()}&lead_id={uuid.uuid4()}"
    query = _next_query(_post_turn(client, query))
    _post_turn(client, query)

    last_call = nodes.llm.calls[-1]
    contents = [m.content for m in last_call]
    assert any("first question about commission" in c for c in contents)
    assert any("second question" in c for c in contents)


def test_language_hint_and_short_reply_stability(call):
    client, repo, stt, jobs, spoken = call([
        "வணக்கம், எனக்கு பார்ட்னர் திட்டம் பற்றி சொல்லுங்கள் எப்படி வேலை செய்கிறது",
        "yes",
    ])
    query = f"?session_id={uuid.uuid4()}&lead_id={uuid.uuid4()}"
    query = _next_query(_post_turn(client, query))
    _post_turn(client, query)

    assert stt.hints == [None, "ta"]          # no hint on turn 1, Tamil afterwards
    assert [lang for _, lang in spoken[:2]] == ["ta", "ta"]  # "yes" does not flip TTS to English
    language_writes = [f for f in repo.written("lead") if "language" in f]
    assert len(language_writes) == 1 and language_writes[0]["language"] == "ta"


def test_cold_signal_ends_call_without_rm_or_requeue(call):
    client, repo, stt, jobs, spoken = call(["no, not interested, stop calling me"])
    _post_turn(client, f"?session_id={uuid.uuid4()}&lead_id={uuid.uuid4()}")
    scores = repo.written("score")
    assert scores and scores[0]["classification"] == "COLD"
    assert not repo.written("rm")
    # COLD must not return to NEW, or the initiator would re-dial it
    assert all(f.get("status") != "NEW" for f in repo.written("lead"))


def _hot_call_twiml(call, monkeypatch, transfer, rm):
    async def fake_choose(repository):
        return rm

    monkeypatch.setattr(w, "choose_rm", fake_choose)
    monkeypatch.setattr(w.get_config(), "live_transfer_enabled", transfer)
    client, repo, stt, jobs, spoken = call(["yes I am interested, connect me"])
    twiml = _post_turn(client, f"?session_id={uuid.uuid4()}&lead_id={uuid.uuid4()}")
    return twiml, jobs


def test_hot_call_is_bridged_to_the_rm_when_transfer_is_on(call, monkeypatch):
    from services.rm_allocator import RM

    twiml, jobs = _hot_call_twiml(call, monkeypatch, True, RM("Asha", "+919800000001"))
    assert "<Dial" in twiml and "<Number>+919800000001</Number>" in twiml
    assert twiml.index("</Dial>") < twiml.index("<Hangup/>"), "must hang up if the RM does not answer"
    assert "send_whatsapp" in [t for t, _ in jobs], "the RM is still notified on WhatsApp"


def test_hot_call_just_hangs_up_when_transfer_is_off_or_rm_has_no_phone(call, monkeypatch):
    from services.rm_allocator import RM

    twiml, _ = _hot_call_twiml(call, monkeypatch, False, RM("Asha", "+919800000001"))
    assert "<Dial" not in twiml and "<Hangup/>" in twiml
    twiml, _ = _hot_call_twiml(call, monkeypatch, True, RM("Asha", None))
    assert "<Dial" not in twiml and "<Hangup/>" in twiml


def test_do_not_contact_request_rejects_the_lead_permanently(call):
    client, repo, stt, jobs, spoken = call(["please don't call me again"])
    _post_turn(client, f"?session_id={uuid.uuid4()}&lead_id={uuid.uuid4()}")
    assert repo.written("score")[0]["classification"] == "COLD"
    statuses = [f.get("status") for f in repo.written("lead")]
    assert "REJECTED" in statuses and "FOLLOW_UP" not in statuses
    assert not repo.written("rm") and "send_whatsapp" not in [t for t, _ in jobs]


def test_stored_turn_shape_scores_without_crashing():
    repo = FakeRepository(history=turns(("tell me more, sounds good", "sure"), ("how does it work?", "like this")))
    engine = ScoringEngine(repo)
    asyncio.run(w._score_and_assign_lead(
        uuid.uuid4(), uuid.uuid4(), repo, engine, FakeQueue([]), classification_override=None
    ))
    scores = repo.written("score")
    assert len(scores) == 1
    assert scores[0]["classification"] in {"HOT", "WARM", "COLD"}


def test_objection_is_logged_then_resolved_when_caller_comes_round(call):
    client, repo, stt, jobs, spoken = call(["That sounds too expensive for me", "ok yes I am interested"])
    query = f"?session_id={uuid.uuid4()}&lead_id={uuid.uuid4()}"
    _post_turn(client, query)
    logged = repo.written("objection")
    assert len(logged) == 1
    assert logged[0]["objection_type"] == "price"
    assert "expensive" in logged[0]["objection_text"]
    assert all(not o["resolved"] for o in repo.objections)

    # the same session continues; the caller now agrees
    _post_turn(client, query)
    assert repo.written("objection_resolved")


def _status(client, **fields):
    lead_id = fields.pop("lead_id", str(uuid.uuid4()))
    session_id = str(uuid.uuid4())
    response = client.post(
        f"/api/webhook/twilio/status?session_id={session_id}&lead_id={lead_id}",
        data={"CallSid": "CA-s", **fields},
    )
    assert response.status_code == 200


@pytest.mark.parametrize("call_status", ["failed", "busy", "no-answer", "canceled"])
def test_unanswered_call_parks_lead_instead_of_crashing(call, call_status):
    client, repo, *_ = call([])
    _status(client, CallStatus=call_status)
    updates = repo.written("lead")
    assert updates and updates[0]["status"] == "FOLLOW_UP"


def test_voicemail_is_parked(call):
    client, repo, *_ = call([])
    _status(client, CallStatus="completed", AnsweredBy="machine_start")
    assert repo.written("lead")[0]["status"] == "FOLLOW_UP"


def test_hangup_before_speaking_is_not_scored(call):
    client, repo, *_ = call([])

    async def contacted(lead_id):
        return {"status": "CONTACTED", "phone": "+91"}

    repo.get_lead = contacted
    _status(client, CallStatus="completed")
    assert repo.written("lead")[0]["status"] == "FOLLOW_UP"
    assert not repo.written("score")
