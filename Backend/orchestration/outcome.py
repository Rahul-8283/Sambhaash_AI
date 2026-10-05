"""
Keyword-based call outcome detection

Matches whole words only, so "I don't know" does not count as "no" and
"yesterday" does not count as "yes".
"""

import json
import re
from typing import Iterable, Optional

HOT_PHRASES = ("yes", "interested")
COLD_PHRASES = ("no", "stop")

_HOT_PATTERN = re.compile(r"\b(?:" + "|".join(map(re.escape, HOT_PHRASES)) + r")\b", re.IGNORECASE)
_COLD_PATTERN = re.compile(r"\b(?:" + "|".join(map(re.escape, COLD_PHRASES)) + r")\b", re.IGNORECASE)


def classify_utterance(text: str) -> Optional[str]:
    """Return "HOT" or "COLD" if the utterance carries a clear signal, else None."""
    if not text:
        return None
    if _HOT_PATTERN.search(text):
        return "HOT"
    if _COLD_PATTERN.search(text):
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
