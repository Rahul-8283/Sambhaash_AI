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


# What the caller hears first on an outbound call, in the lead's saved language.
# en/hi are the original wording; the rest are machine translations and need review
# by a native speaker before going to real leads (same status as the WhatsApp copy).
CALL_GREETINGS = {
    "en": "Hello, this is Rupeezy. Thank you for your interest in our Partner Program. Please speak after the beep.",
    "hi": "नमस्ते, मैं Rupeezy से बोल रहा हूँ। हमारे पार्टनर प्रोग्राम में रुचि दिखाने के लिए धन्यवाद। कृपया बीप के बाद बोलिए।",
    "mr": "नमस्कार, मी Rupeezy कडून बोलत आहे. आमच्या पार्टनर प्रोग्राममध्ये रस दाखवल्याबद्दल धन्यवाद. कृपया बीपनंतर बोला.",
    "bn": "নমস্কার, আমি Rupeezy থেকে বলছি। আমাদের পার্টনার প্রোগ্রামে আগ্রহ দেখানোর জন্য ধন্যবাদ। অনুগ্রহ করে বিপের পরে বলুন।",
    "gu": "નમસ્તે, હું Rupeezy તરફથી વાત કરું છું. અમારા પાર્ટનર પ્રોગ્રામમાં રસ દાખવવા બદલ આભાર. કૃપા કરીને બીપ પછી બોલો.",
    "pa": "ਸਤ ਸ੍ਰੀ ਅਕਾਲ, ਮੈਂ Rupeezy ਵੱਲੋਂ ਬੋਲ ਰਿਹਾ ਹਾਂ। ਸਾਡੇ ਪਾਰਟਨਰ ਪ੍ਰੋਗਰਾਮ ਵਿੱਚ ਦਿਲਚਸਪੀ ਦਿਖਾਉਣ ਲਈ ਧੰਨਵਾਦ। ਕਿਰਪਾ ਕਰਕੇ ਬੀਪ ਤੋਂ ਬਾਅਦ ਬੋਲੋ।",
    "or": "ନମସ୍କାର, ମୁଁ Rupeezy ରୁ କହୁଛି। ଆମ ପାର୍ଟନର ପ୍ରୋଗ୍ରାମରେ ଆଗ୍ରହ ଦେଖାଇଥିବାରୁ ଧନ୍ୟବାଦ। ଦୟାକରି ବୀପ୍ ପରେ କୁହନ୍ତୁ।",
    "ta": "வணக்கம், நான் Rupeezy-யிலிருந்து பேசுகிறேன். எங்கள் பார்ட்னர் திட்டத்தில் ஆர்வம் காட்டியதற்கு நன்றி. பீப் ஒலிக்குப் பிறகு பேசுங்கள்.",
    "te": "నమస్తే, నేను Rupeezy నుండి మాట్లాడుతున్నాను. మా పార్టనర్ ప్రోగ్రామ్‌పై ఆసక్తి చూపినందుకు ధన్యవాదాలు. దయచేసి బీప్ తర్వాత మాట్లాడండి.",
    "kn": "ನಮಸ್ಕಾರ, ನಾನು Rupeezy ಯಿಂದ ಮಾತನಾಡುತ್ತಿದ್ದೇನೆ. ನಮ್ಮ ಪಾರ್ಟ್ನರ್ ಪ್ರೋಗ್ರಾಂನಲ್ಲಿ ಆಸಕ್ತಿ ತೋರಿಸಿದ್ದಕ್ಕೆ ಧನ್ಯವಾದಗಳು. ದಯವಿಟ್ಟು ಬೀಪ್ ನಂತರ ಮಾತನಾಡಿ.",
    "ml": "നമസ്കാരം, ഞാൻ Rupeezy-യിൽ നിന്നാണ് സംസാരിക്കുന്നത്. ഞങ്ങളുടെ പാർട്ണർ പ്രോഗ്രാമിൽ താൽപ്പര്യം കാണിച്ചതിന് നന്ദി. ദയവായി ബീപ്പിന് ശേഷം സംസാരിക്കുക.",
}


def call_greeting(language: str | None) -> tuple[str, str]:
    """(language code, greeting text); unknown languages fall back to English."""
    code = to_language_code(language)
    if code not in CALL_GREETINGS:
        code = "en"
    return code, CALL_GREETINGS[code]
