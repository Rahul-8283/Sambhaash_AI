# services/llm/response_validator.py

from __future__ import annotations

from typing import Any, Dict, List, Optional


class ResponseValidator:
    """
    Validates and sanitizes structured LLM outputs.

    Useful as a safety layer before TTS / DB writes / handoff.
    """

    ALLOWED_STAGES = {
        "intro",
        "pitch",
        "objection",
        "qualification",
        "closing",
        "handoff",
        "follow_up",
    }

    ALLOWED_INTENTS = {
        "curious",
        "interested",
        "hesitant",
        "objection",
        "ready",
        "defer",
        "callback",
        "trust_concern",
        "support_concern",
        "broker_concern",
        "network_concern",
        "unknown",
    }

    ALLOWED_OBJECTIONS = {
        "already_with_broker",
        "no_network",
        "support_concern",
        "trust_concern",
        "call_later",
        None,
    }

    ALLOWED_CLASSIFICATIONS = {"hot", "warm", "cold"}

    def validate_or_fix(self, output: Dict[str, Any], fallback_language: str = "english") -> Dict[str, Any]:
        data = dict(output or {})

        data["reply_text"] = self._clean_text(str(data.get("reply_text", "")))
        data["stage"] = self._normalize_stage(data.get("stage"))
        data["intent"] = self._normalize_intent(data.get("intent"))
        data["objection_type"] = self._normalize_objection(data.get("objection_type"))
        data["confidence"] = self._clamp_float(data.get("confidence", 0.0), 0.0, 1.0)

        data["score_signals"] = self._normalize_score_signals(data.get("score_signals", {}))
        data["handoff_required"] = bool(data.get("handoff_required", False))
        data["whatsapp_required"] = bool(data.get("whatsapp_required", False))

        data["memory_updates"] = self._normalize_memory_updates(data.get("memory_updates", {}))
        data["call_summary"] = self._normalize_call_summary(data.get("call_summary", {}))

        data["language"] = self._normalize_language(data.get("language", fallback_language))
        data["lead_score"] = self._clamp_float(data.get("lead_score", 0.0), 0.0, 100.0)
        data["lead_classification"] = self._normalize_classification(
            data.get("lead_classification") or data["call_summary"].get("interest_level")
        )

        if not data["reply_text"]:
            data["reply_text"] = "Understood. Let me help you with the next step."

        return data

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

    def _normalize_stage(self, value: Any) -> str:
        value = str(value or "").strip().lower()
        return value if value in self.ALLOWED_STAGES else "intro"

    def _normalize_intent(self, value: Any) -> str:
        value = str(value or "").strip().lower()
        return value if value in self.ALLOWED_INTENTS else "unknown"

    def _normalize_objection(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        value = str(value).strip().lower()
        if value in {"none", "null", ""}:
            return None
        return value if value in self.ALLOWED_OBJECTIONS else None

    def _normalize_classification(self, value: Any) -> str:
        value = str(value or "").strip().lower()
        return value if value in self.ALLOWED_CLASSIFICATIONS else "cold"

    def _normalize_language(self, value: Any, fallback: str = "english") -> str:
        value = str(value or fallback).strip().lower()
        allowed = {
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
        return value if value in allowed else fallback

    def _normalize_score_signals(self, value: Any) -> Dict[str, float]:
        default = {
            "intent_signal": 0.0,
            "engagement_signal": 0.0,
            "objection_resolution_signal": 0.0,
            "qualification_signal": 0.0,
            "sentiment_signal": 0.0,
        }
        if not isinstance(value, dict):
            return default
        for key in default:
            default[key] = self._clamp_float(value.get(key, 0.0), 0.0, 1.0)
        return default

    def _normalize_memory_updates(self, value: Any) -> Dict[str, Any]:
        if not isinstance(value, dict):
            return {
                "preferred_language": None,
                "resolved_objections": [],
                "unresolved_objections": [],
                "conversation_summary": "",
                "turn_summary": "",
            }
        return {
            "preferred_language": value.get("preferred_language"),
            "resolved_objections": self._as_string_list(value.get("resolved_objections", [])),
            "unresolved_objections": self._as_string_list(value.get("unresolved_objections", [])),
            "conversation_summary": self._clean_text(str(value.get("conversation_summary", ""))),
            "turn_summary": self._clean_text(str(value.get("turn_summary", ""))),
        }

    def _normalize_call_summary(self, value: Any) -> Dict[str, Any]:
        if not isinstance(value, dict):
            return {
                "topics_covered": [],
                "objections_raised": [],
                "interest_level": "cold",
                "recommended_next_action": "",
                "one_line_summary": "",
            }
        return {
            "topics_covered": self._as_string_list(value.get("topics_covered", [])),
            "objections_raised": self._as_string_list(value.get("objections_raised", [])),
            "interest_level": self._normalize_classification(value.get("interest_level")),
            "recommended_next_action": self._clean_text(str(value.get("recommended_next_action", ""))),
            "one_line_summary": self._clean_text(str(value.get("one_line_summary", ""))),
        }

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