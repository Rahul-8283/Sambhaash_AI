import pytest
from langchain_core.messages import AIMessage, HumanMessage

from orchestration.history import MAX_HISTORY_TURNS, history_to_messages
from utils.phone import normalize_phone


@pytest.mark.parametrize(
    "raw",
    ["+917989683240", "917989683240", "00917989683240", "7989683240", "07989683240", "whatsapp:+917989683240", " +91 79896-83240 "],
)
def test_normalize_phone_to_e164(raw):
    assert normalize_phone(raw, default_country_code="91") == "+917989683240"


@pytest.mark.parametrize("raw", ["", "abc", "123", None])
def test_normalize_phone_rejects_garbage(raw):
    with pytest.raises(ValueError):
        normalize_phone(raw, default_country_code="91")


def test_history_alternates_human_and_ai():
    messages = history_to_messages([{"user": "hi", "ai": "hello"}, {"user": "price?", "ai": "cheap"}])
    assert [type(m) for m in messages] == [HumanMessage, AIMessage, HumanMessage, AIMessage]
    assert messages[2].content == "price?"


def test_history_accepts_json_text_and_ignores_junk():
    assert len(history_to_messages('[{"user": "a", "ai": "b"}]')) == 2
    assert history_to_messages("nope") == []
    assert history_to_messages(None) == []
    assert history_to_messages([None, "x", {"user": "ok"}]) == [HumanMessage(content="ok")]


def test_history_is_bounded():
    many = [{"user": f"u{i}", "ai": f"a{i}"} for i in range(MAX_HISTORY_TURNS + 10)]
    messages = history_to_messages(many)
    assert len(messages) == MAX_HISTORY_TURNS * 2
    assert messages[-1].content == f"a{MAX_HISTORY_TURNS + 9}"
