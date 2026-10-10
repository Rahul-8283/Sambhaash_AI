"""Rate limiting and Twilio signature verification, through a real FastAPI app."""

from types import SimpleNamespace

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from twilio.request_validator import RequestValidator

import api.rate_limit as rate_limit_module
import api.twilio_auth as twilio_auth
from api.rate_limit import client_ip, rate_limit


# ---------- rate limit ----------

class FakeRedis:
    def __init__(self):
        self.counts = {}

    async def set(self, key, value, ex=None, nx=False):
        if nx and key in self.counts:
            return None
        self.counts[key] = value
        return True

    async def incr(self, key):
        self.counts[key] += 1
        return self.counts[key]


def _limited_app(limit=2):
    app = FastAPI()

    @app.post("/lead", dependencies=[Depends(rate_limit("t", limit, 60))])
    async def lead():
        return {"ok": True}

    return TestClient(app)


def test_allows_up_to_the_limit_then_429(monkeypatch):
    monkeypatch.setattr(rate_limit_module, "_redis", lambda: FakeRedis())
    shared = FakeRedis()
    monkeypatch.setattr(rate_limit_module, "_redis", lambda: shared)
    client = _limited_app(limit=2)
    assert client.post("/lead").status_code == 200
    assert client.post("/lead").status_code == 200
    blocked = client.post("/lead")
    assert blocked.status_code == 429
    assert blocked.headers["retry-after"] == "60"


def test_limit_is_per_client_ip(monkeypatch):
    shared = FakeRedis()
    monkeypatch.setattr(rate_limit_module, "_redis", lambda: shared)
    client = _limited_app(limit=1)
    assert client.post("/lead", headers={"x-forwarded-for": "1.1.1.1"}).status_code == 200
    assert client.post("/lead", headers={"x-forwarded-for": "2.2.2.2"}).status_code == 200
    assert client.post("/lead", headers={"x-forwarded-for": "1.1.1.1"}).status_code == 429


def test_fails_open_when_redis_is_down(monkeypatch):
    class Down:
        async def set(self, *a, **k):
            raise ConnectionError("redis down")

    monkeypatch.setattr(rate_limit_module, "_redis", lambda: Down())
    client = _limited_app(limit=1)
    assert client.post("/lead").status_code == 200
    assert client.post("/lead").status_code == 200


def test_client_ip_trusts_last_forwarded_hop():
    request = SimpleNamespace(headers={"x-forwarded-for": "9.9.9.9, 10.0.0.1"}, client=SimpleNamespace(host="127.0.0.1"))
    assert client_ip(request) == "10.0.0.1"


# ---------- Twilio signature ----------

TOKEN = "test-auth-token"


def _twilio_app(monkeypatch, validate=True, token=TOKEN):
    monkeypatch.setattr(
        twilio_auth,
        "get_config",
        lambda: SimpleNamespace(twilio_validate_signatures=validate, twilio_auth_token=token, twilio_webhook_base_url=""),
    )
    app = FastAPI()

    @app.post("/hook", dependencies=[Depends(twilio_auth.verify_twilio_signature)])
    async def hook():
        return {"ok": True}

    return TestClient(app)


def test_valid_signature_passes(monkeypatch):
    client = _twilio_app(monkeypatch)
    params = {"CallSid": "CA1", "From": "+911"}
    signature = RequestValidator(TOKEN).compute_signature("http://testserver/hook", params)
    assert client.post("/hook", data=params, headers={"X-Twilio-Signature": signature}).status_code == 200


def test_tampered_params_are_rejected(monkeypatch):
    client = _twilio_app(monkeypatch)
    signature = RequestValidator(TOKEN).compute_signature("http://testserver/hook", {"CallSid": "CA1"})
    response = client.post("/hook", data={"CallSid": "CA-evil"}, headers={"X-Twilio-Signature": signature})
    assert response.status_code == 403


def test_missing_signature_is_rejected(monkeypatch):
    assert _twilio_app(monkeypatch).post("/hook", data={"a": "b"}).status_code == 403


def test_unconfigured_token_is_503_not_open(monkeypatch):
    client = _twilio_app(monkeypatch, token="sk-test-default")
    assert client.post("/hook", data={"a": "b"}).status_code == 503


def test_validation_can_be_disabled_for_local_debugging(monkeypatch):
    assert _twilio_app(monkeypatch, validate=False).post("/hook", data={"a": "b"}).status_code == 200


def test_forwarded_public_url_is_accepted(monkeypatch):
    client = _twilio_app(monkeypatch)
    params = {"CallSid": "CA1"}
    signature = RequestValidator(TOKEN).compute_signature("https://abc.ngrok-free.app/hook", params)
    headers = {"X-Twilio-Signature": signature, "x-forwarded-proto": "https", "x-forwarded-host": "abc.ngrok-free.app"}
    assert client.post("/hook", data=params, headers=headers).status_code == 200
