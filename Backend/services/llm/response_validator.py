# services/llm/response_validator.py

from __future__ import annotations

from typing import Any, Dict, List


class ResponseValidator:
    """
    Validates and sanitizes structured LLM outputs.

    Useful as a safety layer before TTS / DB writes / handoff.
    """

    ALLOWED_CLASSIFICATIONS = {"hot", "warm", "cold"}

    def validate_summary(self, summary: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(summary or {})
        data["duration_summary"] = self._clean_text(str(data.get("duration_summary", "")))
        data["topics_covered"] = self._as_string_list(data.get("topics_covered", []))
        data["objections_raised"] = self._as_string_list(data.get("objections_raised", []))
        data["interest_score"] = int(self._clamp_float(data.get("interest_score", 0), 0, 100))
        data["lead_classification"] = self._normalize_classification(data.get("lead_classification"))
        data["recommended_next_action"] = self._clean_text(str(data.get("recommended_next_action", "")))
        data["one_line_summary"] = self._clean_text(str(data.get("one_line_summary", "")))
        return data

    def _normalize_classification(self, value: Any) -> str:
        value = str(value or "").strip().lower()
        return value if value in self.ALLOWED_CLASSIFICATIONS else "cold"

    def _as_string_list(self, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(x) for x in value if str(x).strip()]
        if isinstance(value, str):
            return [value] if value.strip() else []
        return [str(value)]

    def _clean_text(self, value: str) -> str:
        return " ".join(value.split()).strip()

    def _clamp_float(self, value: Any, low: float, high: float) -> float:
        try:
            number = float(value)
        except Exception:
            number = low
        return max(low, min(high, number))