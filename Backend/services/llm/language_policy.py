# services/llm/language_policy.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class LanguageDecision:
    response_language: str
    should_mirror_user_style: bool
    should_allow_code_mix: bool


class LanguagePolicy:
    """
    Small policy helper to keep language behavior consistent across turns.
    """

    SUPPORTED = {
        "english",
        "hindi",
        "hinglish",
        "tamil",
        "telugu",
        "marathi",
        "gujarati",
        "bengali",
        "kannada",
    }

    def resolve(
        self,
        preferred_language: Optional[str],
        detected_language: Optional[str],
        fallback: str = "english",
    ) -> LanguageDecision:
        preferred = self._normalize(preferred_language)
        detected = self._normalize(detected_language)
        response_language = preferred or detected or fallback

        if response_language not in self.SUPPORTED:
            response_language = fallback

        should_code_mix = response_language in {"hinglish"}
        should_mirror = True

        return LanguageDecision(
            response_language=response_language,
            should_mirror_user_style=should_mirror,
            should_allow_code_mix=should_code_mix,
        )

    def _normalize(self, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        value = str(value).strip().lower()
        return value if value in self.SUPPORTED else None