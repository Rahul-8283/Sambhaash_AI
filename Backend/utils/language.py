"""
Language normalization

The speech detector returns words ("english", "hindi", "hinglish") while TTS voices,
WhatsApp templates and lead records use short codes ("en", "hi"). Everything that
keys on a language should go through to_language_code().
"""

# Hinglish is spoken in Hindi-leaning speech, so it uses the Hindi voice and templates
_LANGUAGE_NAMES = {
    "english": "en",
    "hindi": "hi",
    "hinglish": "hi",
}


def to_language_code(value: str | None, default: str = "en") -> str:
    """
    Return a 2-letter language code.

    "english" -> "en", "hindi" -> "hi", "hinglish" -> "hi",
    "hi-IN" -> "hi", "TE" -> "te", None or "" -> default
    """
    if not value:
        return default

    text = str(value).strip().lower()
    if text in _LANGUAGE_NAMES:
        return _LANGUAGE_NAMES[text]

    # Region-tagged codes like "hi-IN" or "en_US"
    code = text.replace("_", "-").split("-")[0]
    return code or default
