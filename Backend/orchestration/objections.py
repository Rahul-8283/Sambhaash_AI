"""
Objection typing for the objections_log table.

Keyword based like the rest of the call heuristics: it only has to give a
dashboard something sensible to group by, not understand the caller.
"""

import re

_RULES = (
    ("price", r"expensive|costly|cost|price|fee|fees|charges?|afford|budget|commission"),
    ("trust", r"trust|scam|fraud|fake|genuine|safe|legit|cheat"),
    ("timing", r"later|busy|not now|no time|call back|tomorrow|next week|time"),
    ("not_interested", r"not interested|no interest|don't want|do not want|stop|no thanks|no thank you"),
)
_PATTERNS = [(name, re.compile(rf"\b(?:{expr})\b", re.IGNORECASE)) for name, expr in _RULES]


def classify_objection(text: str) -> str:
    """Return price / trust / timing / not_interested, or "other"."""
    for name, pattern in _PATTERNS:
        if pattern.search(text or ""):
            return name
    return "other"
