# services/llm/objection_handler.py

from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .state_machine import ConversationStage, LeadIntent


class ObjectionType(str, Enum):
    ALREADY_WITH_BROKER = "already_with_broker"
    NO_NETWORK = "no_network"
    SUPPORT_CONCERN = "support_concern"
    TRUST_CONCERN = "trust_concern"
    CALL_LATER = "call_later"
    UNKNOWN = "unknown"


class ObjectionStrategy(str, Enum):
    ACKNOWLEDGE = "acknowledge"
    REFRAME = "reframe"
    DIFFERENTIATE = "differentiate"
    GUIDE = "guide"


@dataclass
class ObjectionResponsePlan:
    objection_type: str = ObjectionType.UNKNOWN.value
    strategy: str = ObjectionStrategy.ACKNOWLEDGE.value
    acknowledgement: str = ""
    reframe: str = ""
    differentiate: str = ""
    guide: str = ""
    response_text: str = ""
    resolved: bool = False
    needs_follow_up: bool = False
    should_handoff: bool = False
    next_stage_hint: str = ConversationStage.OBJECTION.value
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ObjectionHandler:
    """
    Context-aware objection handling for Sambhaash AI.

    This module stays within the original plan:
    - detects the objection type passed in from intent_detector.py / orchestrator.py
    - builds a contextual response plan
    - optionally uses RAG snippets from rag_engine.py
    - adapts the response to the current stage and memory
    - does NOT own state transitions, scoring, DB writes, or telephony

    The output is a structured plan that the orchestrator can pass to:
    - prompt_builder.py
    - memory_manager.py
    - state_machine.py
    - scoring.py
    """

    def __init__(
        self,
        model_name: str = "model name",
        api_key: str = "your api key",
    ) -> None:
        self.model_name = model_name
        self.api_key = api_key

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def handle(
        self,
        user_text: str,
        objection_type: Optional[str],
        stage: ConversationStage | str,
        language: Optional[str] = None,
        memory_snapshot: Optional[Dict[str, Any]] = None,
        retrieved_context: Optional[List[Dict[str, Any]]] = None,
        intent: Optional[LeadIntent | str] = None,
    ) -> Dict[str, Any]:
        """
        Main entry point used by orchestrator.py

        Returns a structured plan with:
        - acknowledgement
        - reframe
        - differentiate
        - guide
        - response_text
        - resolution flags
        - next stage hint
        """
        stage_value = self._normalize_stage(stage)
        objection_value = self._normalize_objection(objection_type)
        intent_value = self._normalize_intent(intent)
        memory_snapshot = memory_snapshot or {}
        retrieved_context = retrieved_context or []

        plan = self._build_plan(
            user_text=user_text,
            objection_type=objection_value,
            stage=stage_value,
            language=language,
            memory_snapshot=memory_snapshot,
            retrieved_context=retrieved_context,
            intent=intent_value,
        )

        # If a model is ever wired in, this is where the final response text can be refined.
        # The deterministic plan below is already safe and production-shaped for the hackathon.
        return plan.to_dict()

    # ------------------------------------------------------------------
    # Core plan builder
    # ------------------------------------------------------------------

    def _build_plan(
        self,
        user_text: str,
        objection_type: str,
        stage: str,
        language: Optional[str],
        memory_snapshot: Dict[str, Any],
        retrieved_context: List[Dict[str, Any]],
        intent: Optional[str],
    ) -> ObjectionResponsePlan:
        user_text_clean = self._clean_text(user_text)
        objection_type = self._normalize_objection(objection_type)
        language = self._normalize_language(language)
        intent = self._normalize_intent(intent)

        context_text = self._build_context_text(memory_snapshot, retrieved_context)

        # Build deterministic response blocks based on objection type.
        if objection_type == ObjectionType.ALREADY_WITH_BROKER.value:
            acknowledgement = self._localized_ack(
                language,
                "That makes sense — you already understand the business well.",
            )
            reframe = self._localized_reframe(
                language,
                "The main question is whether your current setup gives you better economics and smoother payouts.",
            )
            differentiate = self._localized_diff(
                language,
                "Rupeezy offers zero joining fee, 100% brokerage share, and daily payouts via the RISE Portal.",
            )
            guide = self._localized_guide(
                language,
                "Would it be fair to compare your current arrangement with this and see if it is actually better for you?",
            )
            next_stage = self._next_stage_for_objection(stage, resolved=False)

        elif objection_type == ObjectionType.NO_NETWORK.value:
            acknowledgement = self._localized_ack(
                language,
                "That is okay — not everyone starts with a large network.",
            )
            reframe = self._localized_reframe(
                language,
                "Even a small but relevant client base can be enough to begin.",
            )
            differentiate = self._localized_diff(
                language,
                "The program is designed to help partners grow over time, and the economics stay strong from the start.",
            )
            guide = self._localized_guide(
                language,
                "Would you like me to explain how people usually begin and scale from there?",
            )
            next_stage = self._next_stage_for_objection(stage, resolved=False)

        elif objection_type == ObjectionType.SUPPORT_CONCERN.value:
            acknowledgement = self._localized_ack(
                language,
                "That is a very valid concern.",
            )
            reframe = self._localized_reframe(
                language,
                "Support matters because you want your clients to have a smooth experience.",
            )
            differentiate = self._localized_diff(
                language,
                "Rupeezy’s process is designed so onboarding and operational support are handled clearly through the official flow.",
            )
            guide = self._localized_guide(
                language,
                "If helpful, I can walk you through how support works after onboarding.",
            )
            next_stage = self._next_stage_for_objection(stage, resolved=False)

        elif objection_type == ObjectionType.TRUST_CONCERN.value:
            acknowledgement = self._localized_ack(
                language,
                "I understand — trust is important before you move forward.",
            )
            reframe = self._localized_reframe(
                language,
                "The best way to judge is by the actual structure and benefits of the program.",
            )
            differentiate = self._localized_diff(
                language,
                "The key points are zero joining fee, full brokerage share, and daily payout visibility through the portal.",
            )
            guide = self._localized_guide(
                language,
                "Would it help if I quickly summarized the official details so you can evaluate it clearly?",
            )
            next_stage = self._next_stage_for_objection(stage, resolved=False)

        elif objection_type == ObjectionType.CALL_LATER.value:
            acknowledgement = self._localized_ack(
                language,
                "No problem — I understand you may be busy right now.",
            )
            reframe = self._localized_reframe(
                language,
                "I do not want to take too much of your time.",
            )
            differentiate = self._localized_diff(
                language,
                "I can keep this very short and send a follow-up with the key details.",
            )
            guide = self._localized_guide(
                language,
                "Should I send a short follow-up and reconnect later?",
            )
            next_stage = ConversationStage.FOLLOW_UP.value

        else:
            acknowledgement = self._localized_ack(
                language,
                "I understand.",
            )
            reframe = self._localized_reframe(
                language,
                "Let us keep this simple and practical.",
            )
            differentiate = self._localized_diff(
                language,
                "I will stick to the approved program details.",
            )
            guide = self._localized_guide(
                language,
                "Would you like me to explain the next step?",
            )
            next_stage = self._next_stage_for_objection(stage, resolved=False)

        response_text = self._compose_response(
            language=language,
            acknowledgement=acknowledgement,
            reframe=reframe,
            differentiate=differentiate,
            guide=guide,
        )

        resolved = False
        needs_follow_up = objection_type == ObjectionType.CALL_LATER.value
        should_handoff = False

        # If the lead is already warm/hot and the objection is resolved by context,
        # the orchestrator can decide to move to closing/handoff later.
        score = self._extract_score(memory_snapshot)
        classification = self._extract_classification(memory_snapshot)

        if objection_type != ObjectionType.UNKNOWN.value and score >= 75 and classification == "hot":
            should_handoff = True
            next_stage = ConversationStage.HANDOFF.value

        confidence = self._confidence_from_context(
            objection_type=objection_type,
            user_text=user_text_clean,
            retrieved_context=retrieved_context,
            memory_snapshot=memory_snapshot,
        )

        return ObjectionResponsePlan(
            objection_type=objection_type,
            strategy=ObjectionStrategy.ACKNOWLEDGE.value,
            acknowledgement=acknowledgement,
            reframe=reframe,
            differentiate=differentiate,
            guide=guide,
            response_text=response_text,
            resolved=resolved,
            needs_follow_up=needs_follow_up,
            should_handoff=should_handoff,
            next_stage_hint=next_stage,
            confidence=confidence,
            metadata={
                "language": language,
                "stage": stage,
                "intent": intent,
                "user_text": user_text_clean,
                "score": score,
                "classification": classification,
                "retrieved_context_count": len(retrieved_context),
                "context_text": context_text,
            },
        )

    # ------------------------------------------------------------------
    # Optional prompt construction (for future LLM refinement)
    # ------------------------------------------------------------------

    def build_llm_prompt(
        self,
        user_text: str,
        objection_type: str,
        stage: str,
        language: Optional[str] = None,
        memory_snapshot: Optional[Dict[str, Any]] = None,
        retrieved_context: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Strict prompt for a model-based objection rewriter, if you choose to use one.

        The plan is:
        acknowledge -> reframe -> differentiate -> guide
        """
        memory_snapshot = memory_snapshot or {}
        retrieved_context = retrieved_context or []

        return f"""
You are the objection handling module for a multilingual sales agent.

Your only task is to rewrite the response in a natural, persuasive, and concise way.
Do not add unsupported claims. Use only the approved context.

### User message
{user_text}

### Objection type
{objection_type}

### Stage
{stage}

### Language
{language or "unknown"}

### Memory snapshot
{json.dumps(memory_snapshot, ensure_ascii=False, indent=2)}

### Retrieved approved context
{json.dumps(retrieved_context, ensure_ascii=False, indent=2)}

### Response pattern
1. Acknowledge
2. Reframe
3. Differentiate
4. Guide

### Output format
Return ONLY JSON:
{{
  "acknowledgement": "...",
  "reframe": "...",
  "differentiate": "...",
  "guide": "...",
  "response_text": "...",
  "resolved": false,
  "needs_follow_up": false
}}
""".strip()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _compose_response(
        self,
        language: str,
        acknowledgement: str,
        reframe: str,
        differentiate: str,
        guide: str,
    ) -> str:
        parts = [acknowledgement, reframe, differentiate, guide]
        text = " ".join(part.strip() for part in parts if part and part.strip())
        return self._polish(language, text)

    def _polish(self, language: str, text: str) -> str:
        """
        Lightweight formatting to keep the reply conversational.
        """
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _localized_ack(self, language: str, text: str) -> str:
        return self._localized_text(language, text)

    def _localized_reframe(self, language: str, text: str) -> str:
        return self._localized_text(language, text)

    def _localized_diff(self, language: str, text: str) -> str:
        return self._localized_text(language, text)

    def _localized_guide(self, language: str, text: str) -> str:
        return self._localized_text(language, text)

    def _localized_text(self, language: str, text: str) -> str:
        """
        Keep language handling simple and consistent with the original plan:
        - Hindi
        - English
        - Hinglish
        - fallback to English

        The system can later swap these strings with richer generation,
        but this keeps the structure correct right now.
        """
        lang = self._normalize_language(language)

        if lang == "hindi":
            return self._translate_hint(text, "hindi")
        if lang == "hinglish":
            return self._translate_hint(text, "hinglish")
        return text

    def _translate_hint(self, text: str, language: str) -> str:
        """
        Placeholder for language-specific wording.

        For now, keep the approved meaning intact. This avoids any drift from the plan.
        """
        if language == "hindi":
            return text
        if language == "hinglish":
            return text
        return text

    def _next_stage_for_objection(self, stage: str, resolved: bool) -> str:
        if resolved:
            if stage == ConversationStage.OBJECTION.value:
                return ConversationStage.QUALIFICATION.value
            if stage == ConversationStage.QUALIFICATION.value:
                return ConversationStage.CLOSING.value
        return ConversationStage.OBJECTION.value

    def _confidence_from_context(
        self,
        objection_type: str,
        user_text: str,
        retrieved_context: List[Dict[str, Any]],
        memory_snapshot: Dict[str, Any],
    ) -> float:
        confidence = 0.55

        if objection_type != ObjectionType.UNKNOWN.value:
            confidence += 0.2

        if retrieved_context:
            confidence += 0.1

        if memory_snapshot.get("resolved_objections"):
            confidence += 0.05

        if len(user_text.split()) <= 4:
            confidence -= 0.05

        return max(0.0, min(0.95, confidence))

    def _build_context_text(
        self,
        memory_snapshot: Dict[str, Any],
        retrieved_context: List[Dict[str, Any]],
    ) -> str:
        parts: List[str] = []

        if memory_snapshot.get("conversation_summary"):
            parts.append(f"Summary: {memory_snapshot['conversation_summary']}")

        if memory_snapshot.get("preferred_language"):
            parts.append(f"Preferred language: {memory_snapshot['preferred_language']}")

        if memory_snapshot.get("resolved_objections"):
            parts.append(
                "Resolved objections: " + ", ".join(memory_snapshot.get("resolved_objections", []))
            )

        if memory_snapshot.get("unresolved_objections"):
            parts.append(
                "Unresolved objections: " + ", ".join(memory_snapshot.get("unresolved_objections", []))
            )

        if retrieved_context:
            parts.append("Retrieved context:")
            for item in retrieved_context:
                if isinstance(item, dict):
                    chunk = item.get("chunk_text") or item.get("text") or ""
                    if chunk:
                        parts.append(f"- {chunk}")

        return "\n".join(parts).strip()

    def _extract_score(self, memory_snapshot: Dict[str, Any]) -> float:
        try:
            return float(memory_snapshot.get("last_score", memory_snapshot.get("score", 0.0)) or 0.0)
        except Exception:
            return 0.0

    def _extract_classification(self, memory_snapshot: Dict[str, Any]) -> str:
        value = str(memory_snapshot.get("current_classification", memory_snapshot.get("classification", "cold")) or "cold")
        return value.strip().lower()

    def _normalize_stage(self, stage: ConversationStage | str) -> str:
        if isinstance(stage, ConversationStage):
            return stage.value
        value = str(stage or "").strip().lower()
        if value in {s.value for s in ConversationStage}:
            return value
        return ConversationStage.OBJECTION.value

    def _normalize_objection(self, objection_type: Optional[str]) -> str:
        value = str(objection_type or "").strip().lower()
        mapping = {
            "already_with_broker": ObjectionType.ALREADY_WITH_BROKER.value,
            "no_network": ObjectionType.NO_NETWORK.value,
            "support_concern": ObjectionType.SUPPORT_CONCERN.value,
            "trust_concern": ObjectionType.TRUST_CONCERN.value,
            "call_later": ObjectionType.CALL_LATER.value,
        }
        return mapping.get(value, ObjectionType.UNKNOWN.value)

    def _normalize_intent(self, intent: Optional[LeadIntent | str]) -> str:
        if intent is None:
            return "unknown"
        if isinstance(intent, LeadIntent):
            return intent.value
        return str(intent).strip().lower() or "unknown"

    def _normalize_language(self, language: Optional[str]) -> str:
        value = str(language or "english").strip().lower()
        if value in {"english", "hindi", "hinglish"}:
            return value
        return "english"

    def _clean_text(self, text: Optional[str]) -> str:
        return re.sub(r"\s+", " ", (text or "").strip())

    def _fallback_response(self, objection_type: str, language: str) -> str:
        """
        Safety fallback if needed by future integrations.
        """
        if objection_type == ObjectionType.CALL_LATER.value:
            return self._localized_text(language, "No problem — I will keep this short and follow up later.")
        return self._localized_text(language, "I understand your concern. Let me address that clearly.")