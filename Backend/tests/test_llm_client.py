import json

import httpx
import pytest

from services.llm.llm_client import LLMClient, LLMClientError


def _client(handler):
    client = LLMClient(model_name="m", api_key="key", base_url="https://llm.test/v1")
    client._client = httpx.Client(transport=httpx.MockTransport(handler))
    return client


def test_sends_honest_user_agent_and_parses_reply():
    seen = {}

    def handler(request):
        seen["ua"] = request.headers["user-agent"]
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "```json\n{\"a\": 1}\n```"}}]})

    client = _client(handler)
    assert client.generate_json("give json") == {"a": 1}
    assert "Mozilla" not in seen["ua"] and seen["ua"].startswith("SambhaashAI")
    assert seen["auth"] == "Bearer key"
    assert seen["body"]["model"] == "m"


def test_http_error_becomes_llm_client_error():
    client = _client(lambda request: httpx.Response(404, json={"error": "model_not_found"}))
    with pytest.raises(LLMClientError) as exc:
        client.generate("hi")
    assert "404" in str(exc.value)


def test_missing_content_is_an_error():
    client = _client(lambda request: httpx.Response(200, json={"choices": []}))
    with pytest.raises(LLMClientError):
        client.generate("hi")


def test_placeholder_key_is_rejected_before_any_request():
    client = LLMClient(model_name="m", api_key="your api key")
    with pytest.raises(LLMClientError):
        client.generate("hi")
