# services/llm/prompt_builder.py

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional, Sequence


@dataclass
class PromptBundle:
    """Prompt package accepted by LLMClient."""
    system_prompt: str
    user_prompt: str
    response_format: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PromptBuilder:
    """Builds the post-call summary prompt used by SummaryGenerator."""

    def __init__(self, assistant_name: str = "Sambhaash AI") -> None:
        self.assistant_name = assistant_name

    def build_summary_prompt(
        self,
        memory_snapshot: Dict[str, Any],
        transcript: Sequence[Dict[str, Any] | str],
        final_score: Optional[float] = None,
        final_classification: Optional[str] = None,
        next_action: Optional[str] = None,
    ) -> str:
        """
        Builds a post-call summary prompt.

        This is useful for generating:
        - call duration summary
        - topics covered
        - objections raised
        - final interest score
        - recommended next action
        """
        transcript_block = self._format_transcript(transcript)
        memory_block = self._format_memory_section(memory_snapshot)

        prompt = f"""
You are the summary generation layer for {self.assistant_name}.

Your job is to produce a concise, structured post-call summary.
Use only the transcript and memory given below.
Do not invent details that are not supported.

### MEMORY
{memory_block}

### TRANSCRIPT
{transcript_block}

### FINAL SCORE
{final_score if final_score is not None else memory_snapshot.get("last_score", 0.0)}

### FINAL CLASSIFICATION
{final_classification if final_classification is not None else memory_snapshot.get("current_classification", "cold")}

### NEXT ACTION
{next_action or "unknown"}

### OUTPUT RULES
Return strict JSON only with:
{{
  "duration_summary": "...",
  "topics_covered": ["..."],
  "objections_raised": ["..."],
  "interest_score": 0,
  "lead_classification": "hot|warm|cold",
  "recommended_next_action": "...",
  "one_line_summary": "..."
}}

Do not add markdown, explanations, or extra keys.
""".strip()
        return prompt

    # ------------------------------------------------------------------
    # System prompt
    # ------------------------------------------------------------------

    def _format_transcript(self, transcript: Sequence[Dict[str, Any] | str]) -> str:
        if not transcript:
            return "No transcript available."
            
        lines = []
        for turn in transcript:
            if isinstance(turn, str):
                lines.append(turn)
            elif isinstance(turn, dict):
                # Handle custom Sambhaash format (user/ai keys)
                if "user" in turn:
                    lines.append(f"USER: {turn['user']}")
                if "ai" in turn:
                    lines.append(f"AI: {turn['ai']}")
                
                # Handle standard OpenAI/Langchain style dicts if present
                if "role" in turn:
                    text = turn.get("text") or turn.get("content") or ""
                    if text:
                        lines.append(f"{str(turn['role']).upper()}: {text}")
        
        return "\n".join(lines)

    def _format_memory_section(self, memory_snapshot: Dict[str, Any]) -> str:
        if not memory_snapshot:
            return "No memory available."

        lines: List[str] = []

        if memory_snapshot.get("preferred_language"):
            lines.append(f"Preferred language: {memory_snapshot.get('preferred_language')}")

        if memory_snapshot.get("current_classification"):
            lines.append(f"Current classification: {memory_snapshot.get('current_classification')}")

        if memory_snapshot.get("last_score") is not None:
            lines.append(f"Last score: {memory_snapshot.get('last_score')}")

        lead_profile = memory_snapshot.get("lead_profile") or {}
        if lead_profile:
            profile_items = []
            for key in (
                "name",
                "phone",
                "profession",
                "has_existing_clients",
                "network_size",
                "source",
            ):
                value = lead_profile.get(key)
                if value not in (None, "", [], {}, ()):
                    profile_items.append(f"{key}={value}")
            if profile_items:
                lines.append("Lead profile: " + "; ".join(profile_items))

        if memory_snapshot.get("conversation_summary"):
            lines.append(f"Conversation summary: {memory_snapshot.get('conversation_summary')}")

        if memory_snapshot.get("resolved_objections"):
            lines.append(
                "Resolved objections: " + ", ".join(map(str, memory_snapshot.get("resolved_objections", [])))
            )

        if memory_snapshot.get("unresolved_objections"):
            lines.append(
                "Unresolved objections: " + ", ".join(map(str, memory_snapshot.get("unresolved_objections", [])))
            )

        if memory_snapshot.get("call_count") is not None:
            lines.append(f"Call count: {memory_snapshot.get('call_count')}")

        if memory_snapshot.get("last_session_id"):
            lines.append(f"Last session ID: {memory_snapshot.get('last_session_id')}")

        return "\n".join(lines).strip() if lines else "No memory available."
