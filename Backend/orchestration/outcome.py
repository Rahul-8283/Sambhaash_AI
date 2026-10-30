"""
Keyword-based call outcome detection

Matches whole words only, so "I don't know" does not count as "no" and
"yesterday" does not count as "yes".

A bare "no"/"stop" only ends the call when it stands alone. Inside a longer
sentence it is usually a discourse marker, not a refusal: a live call ended on
"No, just tell me what this project is about and what you actually do" -- a
request for information that was scored COLD and hung up on.
"""

import json
import re
from typing import Iterable, Optional

HOT_PHRASES = ("yes", "interested")
COLD_PHRASES = ("no", "stop")

_HOT_PATTERN = re.compile(r"\b(?:" + "|".join(map(re.escape, HOT_PHRASES)) + r")\b", re.IGNORECASE)
_COLD_PATTERN = re.compile(r"\b(?:" + "|".join(map(re.escape, COLD_PHRASES)) + r")\b", re.IGNORECASE)


# "not interested" contains "interested": a refusal must not be read as interest
_NEGATED_INTEREST = re.compile(
    r"\b(?:not|never|no|\w+n't)\s+(?:\w+\s+){0,2}interested\b",
    re.IGNORECASE,
)


# A standalone refusal is short ("no", "no thanks", "no, stop calling"). Longer
# utterances containing "no" are treated as unsignalled, so the call continues.
_MAX_BARE_REFUSAL_WORDS = 3


# "don't call me again", "stop calling", "remove my number", "mujhe call mat karo".
# A caller who says this must never be dialled or messaged again.
_DO_NOT_CONTACT = re.compile(
    r"\b(?:do not|don't|dont|never|stop)\s+(?:\w+\s+){0,2}(?:call|calling|contact|disturb|message|messaging|text)\b"
    r"|\bremove\s+(?:me|my\s+(?:number|name))\b|\bdo not disturb\b|\bdnd\b|\bunsubscribe\b"
    r"|\b(?:call|phone|message|msg)\s+mat\s+(?:karo|karna|kijiye)\b",
    re.IGNORECASE,
)


def is_do_not_contact(text: str) -> bool:
    return bool(text) and bool(_DO_NOT_CONTACT.search(text))


def _is_bare_refusal(text: str) -> bool:
    """True when the whole utterance is a short refusal rather than a sentence."""
    if "?" in text:
        return False
    return len(text.split()) <= _MAX_BARE_REFUSAL_WORDS


def classify_utterance(text: str) -> Optional[str]:
    """Return "HOT" or "COLD" if the utterance carries a clear signal, else None."""
    if not text:
        return None
    if is_do_not_contact(text):
        return "COLD"
    if _NEGATED_INTEREST.search(text):
        return "COLD"
    if _HOT_PATTERN.search(text):
        return "HOT"
    if _COLD_PATTERN.search(text) and _is_bare_refusal(text):
        return "COLD"
    return None


def classify_outcome(user_texts_newest_first: Iterable[str]) -> str:
    """
    Decide the call outcome from everything the caller said.

    The newest utterance with a clear signal wins. With no signal at all, the
    lead is WARM.
    """
    for text in user_texts_newest_first:
        signal = classify_utterance(text)
        if signal:
            return signal
    return "WARM"


def user_texts_from_history(history) -> list[str]:
    """
    Pull the caller's utterances, newest first, from stored conversation history.
    History is a list of {"user": ..., "ai": ...} turns, or JSON text of that list.
    """
    if isinstance(history, str):
        try:
            history = json.loads(history)
        except ValueError:
            return []
    if not isinstance(history, list):
        return []
    return [str(turn["user"]) for turn in reversed(history) if isinstance(turn, dict) and turn.get("user")]
