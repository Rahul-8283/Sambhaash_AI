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


LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "mr": "Marathi",
    "bn": "Bengali",
    "pa": "Punjabi",
    "gu": "Gujarati",
    "or": "Odia",
    "ta": "Tamil",
    "te": "Telugu",
    "kn": "Kannada",
    "ml": "Malayalam",
}


def reply_language_instruction(language: str | None) -> str:
    """
    System-prompt line telling the model which language to answer in.
    Hinglish callers get Hindi-English mix, which is how they speak.
    """
    code = to_language_code(language)
    if (language or "").lower() == "hinglish":
        return "Reply in Hinglish: simple Hindi written in English letters, mixed with English words, the way the caller speaks."
    name = LANGUAGE_NAMES.get(code, "English")
    return f"Always reply in {name}, the language the caller is speaking."


# Fewer words than this carry no reliable language signal ("yes", "haan", "ok")
MIN_WORDS_FOR_LANGUAGE = 3


def call_language(detected: str | None, transcript: str, previous: str | None) -> tuple[str, bool]:
    """
    Language to use for this turn, and whether the detection is confident enough
    to store on the lead.

    Very short replies are ambiguous (a Tamil caller saying "yes" detects as
    English), so they keep the language already established on the call.
    """
    confident = len((transcript or "").split()) >= MIN_WORDS_FOR_LANGUAGE
    if not confident and previous:
        return previous, False
    return (detected or previous or "en"), confident


def last_turn_language(history) -> str | None:
    """Language of the most recent stored turn, or None for a call with no turns."""
    import json

    if isinstance(history, str):
        try:
            history = json.loads(history)
        except ValueError:
            return None
    if not isinstance(history, list):
        return None
    for turn in reversed(history):
        if isinstance(turn, dict) and turn.get("language"):
            return str(turn["language"])
    return None
