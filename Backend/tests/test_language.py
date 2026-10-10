import pytest

from services.stt.language_detector import LanguageDetector
from utils.language import (
    call_language,
    last_turn_language,
    reply_language_instruction,
    to_language_code,
)


@pytest.mark.parametrize(
    "value,expected",
    [("english", "en"), ("hindi", "hi"), ("hinglish", "hi"), ("hi-IN", "hi"), ("TE", "te"), (None, "en"), ("", "en")],
)
def test_to_language_code(value, expected):
    assert to_language_code(value) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("வணக்கம் எனக்கு உதவி வேண்டும்", "ta"),
        ("నాకు సహాయం కావాలి", "te"),
        ("আমার সাহায্য দরকার", "bn"),
        ("ਮੈਨੂੰ ਮਦਦ ਚਾਹੀਦੀ ਹੈ", "pa"),
        ("મને મદદ જોઈએ છે", "gu"),
        ("ನನಗೆ ಸಹಾಯ ಬೇಕು", "kn"),
        ("എനിക്ക് സഹായം വേണം", "ml"),
        ("मुझे मदद चाहिए", "hi"),
        ("I would like to know more about the program", "en"),
        ("mujhe batao kya hai ye", "hinglish"),
        ("", "en"),
    ],
)
def test_detector(text, expected):
    assert LanguageDetector.detect_language(text) == expected


def test_short_reply_keeps_established_language():
    assert call_language("en", "yes", "ta") == ("ta", False)
    assert call_language("en", "yes", None) == ("en", False)


def test_long_reply_switches_and_is_confident():
    assert call_language("hi", "haan mujhe poori jaankari chahiye", "en") == ("hi", True)


def test_last_turn_language():
    assert last_turn_language('[{"user":"a","ai":"b","language":"te"}]') == "te"
    assert last_turn_language([{"user": "a"}, {"user": "b", "language": "ta"}]) == "ta"
    assert last_turn_language([]) is None
    assert last_turn_language("garbage") is None


def test_reply_instruction_names_language():
    assert "Tamil" in reply_language_instruction("ta")
    assert "Hinglish" in reply_language_instruction("hinglish")
    assert "English" in reply_language_instruction(None)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("मुझे मदद चाहिए", "hi"),
        ("मुझे कमीशन कितना मिलेगा", "hi"),
        ("मला मदत हवी आहे", "mr"),
        ("मला कमिशन किती मिळेल", "mr"),
        ("तुम्ही काय करता", "mr"),
        ("नमस्कार मी रोहित बोलतोय", "mr"),
    ],
)
def test_hindi_vs_marathi(text, expected):
    assert LanguageDetector.detect_language(text) == expected
