import io
import wave

import pytest

from services.messaging.whatsapp_service import WhatsAppService
from services.stt.whisper_service import WHISPER_LANGUAGES
from services.telephony.call_manager import join_wavs, split_for_tts


def _wav(frames: int, rate: int = 8000) -> bytes:
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x01\x00" * frames)
    return out.getvalue()


def test_short_text_is_not_split():
    assert split_for_tts("Hello there.") == ["Hello there."]
    assert split_for_tts("One long sentence without any terminator " * 3) == [("One long sentence without any terminator " * 3).strip()]


def test_split_balances_halves_and_loses_nothing():
    text = "Sentence one is here. " * 2 + "Sentence three is a bit longer than the others. " + "Last one."
    parts = split_for_tts(text)
    assert len(parts) == 2
    assert " ".join(parts).split() == text.split()


def test_split_handles_devanagari_danda():
    text = "रुपीज़ी पार्टनर प्रोग्राम से आप कमीशन कमा सकते हैं। आपको हर क्लाइंट की फीस का हिस्सा मिलता है। क्या मैं विवरण बताऊँ?"
    assert len(split_for_tts(text)) == 2


def test_join_wavs_concatenates_audio():
    joined = join_wavs([_wav(100), _wav(250)])
    with wave.open(io.BytesIO(joined), "rb") as w:
        assert w.getnframes() == 350
        assert w.getframerate() == 8000


def test_join_wavs_rejects_mixed_formats():
    with pytest.raises(ValueError):
        join_wavs([_wav(10, 8000), _wav(10, 16000)])


def test_every_follow_up_template_formats():
    keys = [k for k in WhatsAppService.TEMPLATES if k.startswith("warm_follow_up_")]
    assert {"en", "hi", "mr", "bn", "gu", "pa", "or", "ta", "te", "kn", "ml"} <= {k.rsplit("_", 1)[1] for k in keys}
    for key in keys:
        text = WhatsAppService.TEMPLATES[key]["message"].format(name="Asha", lead_id="L1", phone_number="+91-99")
        assert "Asha" in text and "L1" in text


def test_conversion_templates_cover_en_and_hi():
    for key in ("conversion_en", "conversion_hi"):
        WhatsAppService.TEMPLATES[key]["message"].format(name="A", amount=5000, tenure=12, interest_rate=8.5, lead_id="L")


def test_whisper_languages_exclude_odia():
    assert "or" not in WHISPER_LANGUAGES and {"en", "hi", "ta"} <= WHISPER_LANGUAGES
