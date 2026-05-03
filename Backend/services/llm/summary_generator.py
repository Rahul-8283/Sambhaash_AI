# services/llm/summary_generator.py

from __future__ import annotations

import json
from typing import Any, Dict, Optional, Sequence

from .llm_client import LLMClient
from .prompt_builder import PromptBuilder
from .response_validator import ResponseValidator


class SummaryGenerator:
    """
    Standalone helper for post-call summaries.

    This is useful for workers, dashboards, and RM handoff flows.
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        prompt_builder: Optional[PromptBuilder] = None,
        validator: Optional[ResponseValidator] = None,
    ) -> None:
        self.llm_client = llm_client
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.validator = validator or ResponseValidator()

    def generate(
        self,
        memory_snapshot: Dict[str, Any],
        transcript: Sequence[Dict[str, Any] | str],
        final_score: Optional[float] = None,
        final_classification: Optional[str] = None,
        next_action: Optional[str] = None,
    ) -> Dict[str, Any]:
        prompt = self.prompt_builder.build_summary_prompt(
            memory_snapshot=memory_snapshot,
            transcript=transcript,
            final_score=final_score,
            final_classification=final_classification,
            next_action=next_action,
        )

        if self.llm_client is None:
            return self._fallback_summary(
                memory_snapshot=memory_snapshot,
                transcript=transcript,
                final_score=final_score,
                final_classification=final_classification,
                next_action=next_action,
            )

        raw = self.llm_client.generate(prompt)
        parsed = self._parse_json(raw)

        if not parsed:
            return self._fallback_summary(
                memory_snapshot=memory_snapshot,
                transcript=transcript,
                final_score=final_score,
                final_classification=final_classification,
                next_action=next_action,
            )

        return self.validator.validate_summary(parsed)

    def _fallback_summary(
        self,
        memory_snapshot: Dict[str, Any],
        transcript: Sequence[Dict[str, Any] | str],
        final_score: Optional[float],
        final_classification: Optional[str],
        next_action: Optional[str],
    ) -> Dict[str, Any]:
        topic_count = len(transcript) if transcript else 0
        objections = memory_snapshot.get("unresolved_objections", []) or []
        summary = {
            "duration_summary": "",
            "topics_covered": [],
            "objections_raised": list(objections),
            "interest_score": int(final_score or memory_snapshot.get("last_score", 0) or 0),
            "lead_classification": (final_classification or memory_snapshot.get("current_classification", "cold") or "cold"),
            "recommended_next_action": next_action or "nurture",
            "one_line_summary": f"Conversation captured with {topic_count} turns.",
        }
        return self.validator.validate_summary(summary)

    def _parse_json(self, raw: str) -> Optional[Dict[str, Any]]:
        if not raw:
            return None
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
            return None
        except Exception:
            return None