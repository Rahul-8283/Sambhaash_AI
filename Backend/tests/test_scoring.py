import json

from services.scoring.intent_score import IntentScoreCalculator
from services.scoring.scoring_engine import ScoringEngine

engine = ScoringEngine(repository=None)


def test_extracts_callers_from_stored_turns_json_or_list():
    history = [{"user": "hello there", "ai": "hi"}, {"user": "tell me more", "ai": "sure"}]
    assert engine.extract_user_messages(history) == ["hello there", "tell me more"]
    assert engine.extract_user_messages(json.dumps(history)) == ["hello there", "tell me more"]


def test_extracts_chat_style_turns_and_skips_blanks():
    history = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "yo"}, {"user": "  "}]
    assert engine.extract_user_messages(history) == ["hi"]
    assert engine.extract_user_messages(None) == []
    assert engine.extract_user_messages("not json") == []


def test_negative_interest_phrases_win_over_substrings():
    assert IntentScoreCalculator.extract_interest_level(["not interested"]) < 0.2
    assert IntentScoreCalculator.extract_interest_level(["I am interested"]) > 0.8


def test_keen_caller_outscores_hostile_caller():
    keen = [{"user": "Tell me more, I am definitely interested, sounds good", "ai": "x"}]
    hostile = [{"user": "not interested, waste of time, too expensive", "ai": "x"}]
    assert engine.score_conversation(keen, 120)["composite_score"] > engine.score_conversation(hostile, 120)["composite_score"]


def test_result_shape_and_bounds():
    result = engine.score_conversation([{"user": "okay maybe", "ai": "x"}], 30)
    for key in ("composite_score", "intent_score", "engagement_score", "sentiment_score"):
        assert 0.0 <= result[key] <= 1.0
    assert result["classification"] in {"HOT", "WARM", "COLD"}


def test_empty_conversation_does_not_crash():
    assert engine.score_conversation([], 0)["classification"] in {"HOT", "WARM", "COLD"}
    assert engine.score_conversation("[]", 0)["composite_score"] >= 0


def test_thresholds():
    assert engine.classify_lead(0.80).value == "HOT"
    assert engine.classify_lead(0.60).value == "WARM"
    assert engine.classify_lead(0.20).value == "COLD"
