# services/llm/state_machine.py

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class ConversationStage(str, Enum):
    INTRO = "intro"
    PITCH = "pitch"
    OBJECTION = "objection"
    QUALIFICATION = "qualification"
    CLOSING = "closing"
    HANDOFF = "handoff"
    FOLLOW_UP = "follow_up"


class LeadIntent(str, Enum):
    """Intent labels used by the orchestrator and scoring layer."""
    UNKNOWN = "unknown"
    CURIOUS = "curious"
    INTERESTED = "interested"
    HESITANT = "hesitant"
    OBJECTION = "objection"
    READY = "ready"
    DEFER = "defer"
    CALLBACK = "callback"
    TRUST_CONCERN = "trust_concern"
    SUPPORT_CONCERN = "support_concern"
    BROKER_CONCERN = "broker_concern"
    NETWORK_CONCERN = "network_concern"


@dataclass
class StageDecision:
    """
    Structured result returned by the state machine.
    This keeps the orchestrator clean and predictable.
    """
    current_stage: ConversationStage
    next_stage: ConversationStage
    reason: str
    should_handoff: bool = False
    should_follow_up: bool = False
    should_continue: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationContext:
    """
    Minimal state object for one call session.
    The orchestrator can enrich this with lead/profile/memory data.
    """
    stage: ConversationStage = ConversationStage.INTRO
    intent: LeadIntent = LeadIntent.UNKNOWN
    objections_seen: List[str] = field(default_factory=list)
    objections_resolved: List[str] = field(default_factory=list)
    preferred_language: Optional[str] = None
    total_score: float = 0.0
    classification: str = "cold"
    turn_count: int = 0
    last_user_text: str = ""
    last_assistant_text: str = ""
    flags: Dict[str, Any] = field(default_factory=dict)


class StateMachine:
    """
    Conversation flow controller for Sambhaash AI.

    This file intentionally owns only stage transitions and flow control.
    It does not handle STT, prompt building, scoring math, DB writes,
    TTS, or telephony. Those remain in their respective modules.
    """

    def __init__(self) -> None:
        self._valid_transitions: Dict[ConversationStage, Set[ConversationStage]] = {
            ConversationStage.INTRO: {
                ConversationStage.PITCH,
                ConversationStage.OBJECTION,
                ConversationStage.QUALIFICATION,
                ConversationStage.CLOSING,
                ConversationStage.FOLLOW_UP,
            },
            ConversationStage.PITCH: {
                ConversationStage.OBJECTION,
                ConversationStage.QUALIFICATION,
                ConversationStage.CLOSING,
                ConversationStage.HANDOFF,
                ConversationStage.FOLLOW_UP,
            },
            ConversationStage.OBJECTION: {
                ConversationStage.PITCH,
                ConversationStage.QUALIFICATION,
                ConversationStage.CLOSING,
                ConversationStage.HANDOFF,
                ConversationStage.FOLLOW_UP,
            },
            ConversationStage.QUALIFICATION: {
                ConversationStage.CLOSING,
                ConversationStage.OBJECTION,
                ConversationStage.HANDOFF,
                ConversationStage.FOLLOW_UP,
            },
            ConversationStage.CLOSING: {
                ConversationStage.HANDOFF,
                ConversationStage.FOLLOW_UP,
            },
            ConversationStage.HANDOFF: {
                ConversationStage.FOLLOW_UP,
            },
            ConversationStage.FOLLOW_UP: {
                ConversationStage.FOLLOW_UP,
            },
        }

    def initial_context(self) -> ConversationContext:
        return ConversationContext()

    def is_valid_transition(
        self,
        current_stage: ConversationStage,
        next_stage: ConversationStage,
    ) -> bool:
        return next_stage in self._valid_transitions.get(current_stage, set())

    def determine_stage(
        self,
        current_stage: ConversationStage,
        intent: LeadIntent = LeadIntent.UNKNOWN,
        total_score: float = 0.0,
        classification: str = "cold",
        objections_open: Optional[List[str]] = None,
        objections_resolved: Optional[List[str]] = None,
        lead_ready: bool = False,
        asked_to_call_later: bool = False,
        handoff_requested: bool = False,
    ) -> StageDecision:
        """
        Decide the next stage based on current stage + conversation signals.

        This stays aligned with the original plan:
        intro -> pitch -> objection -> qualification -> closing -> handoff / follow_up
        """

        objections_open = objections_open or []
        objections_resolved = objections_resolved or []

        # Highest-priority transitions first.
        if handoff_requested or classification.lower() == "hot" or total_score >= 75:
            if current_stage != ConversationStage.HANDOFF:
                return StageDecision(
                    current_stage=current_stage,
                    next_stage=ConversationStage.HANDOFF,
                    reason="Lead is qualified for human RM handoff.",
                    should_handoff=True,
                    should_follow_up=False,
                    should_continue=False,
                    metadata={
                        "classification": classification,
                        "total_score": total_score,
                        "intent": intent.value,
                    },
                )

        if asked_to_call_later or intent in {LeadIntent.DEFER, LeadIntent.CALLBACK}:
            return StageDecision(
                current_stage=current_stage,
                next_stage=ConversationStage.FOLLOW_UP,
                reason="Lead requested a later follow-up.",
                should_handoff=False,
                should_follow_up=True,
                should_continue=False,
                metadata={
                    "classification": classification,
                    "total_score": total_score,
                    "intent": intent.value,
                },
            )

        if classification.lower() == "warm" or (40 <= total_score < 75):
            # Warm leads can continue a little longer, but usually go to follow-up
            # once the core pitch and objections are addressed.
            if current_stage in {ConversationStage.CLOSING, ConversationStage.QUALIFICATION}:
                return StageDecision(
                    current_stage=current_stage,
                    next_stage=ConversationStage.FOLLOW_UP,
                    reason="Lead is warm and should receive follow-up.",
                    should_handoff=False,
                    should_follow_up=True,
                    should_continue=False,
                    metadata={
                        "classification": classification,
                        "total_score": total_score,
                        "intent": intent.value,
                    },
                )

        if current_stage == ConversationStage.INTRO:
            if intent in {
                LeadIntent.CURIOUS,
                LeadIntent.INTERESTED,
                LeadIntent.READY,
            }:
                return StageDecision(
                    current_stage=current_stage,
                    next_stage=ConversationStage.PITCH,
                    reason="Lead responded positively to the introduction.",
                    metadata={"intent": intent.value},
                )

            if intent in {
                LeadIntent.OBJECTION,
                LeadIntent.TRUST_CONCERN,
                LeadIntent.SUPPORT_CONCERN,
                LeadIntent.BROKER_CONCERN,
                LeadIntent.NETWORK_CONCERN,
                LeadIntent.HESITANT,
            }:
                return StageDecision(
                    current_stage=current_stage,
                    next_stage=ConversationStage.OBJECTION,
                    reason="Lead raised a concern during the introduction.",
                    metadata={"intent": intent.value, "objections_open": objections_open},
                )

            return StageDecision(
                current_stage=current_stage,
                next_stage=ConversationStage.INTRO,
                reason="Continue the opening and establish rapport.",
                metadata={"intent": intent.value},
            )

        if current_stage == ConversationStage.PITCH:
            if objections_open:
                return StageDecision(
                    current_stage=current_stage,
                    next_stage=ConversationStage.OBJECTION,
                    reason="An objection needs to be addressed before proceeding.",
                    metadata={"objections_open": objections_open},
                )

            if lead_ready or intent == LeadIntent.READY:
                return StageDecision(
                    current_stage=current_stage,
                    next_stage=ConversationStage.CLOSING,
                    reason="Lead appears ready to proceed.",
                    metadata={"intent": intent.value},
                )

            if intent in {
                LeadIntent.CURIOUS,
                LeadIntent.INTERESTED,
                LeadIntent.HESITANT,
            }:
                return StageDecision(
                    current_stage=current_stage,
                    next_stage=ConversationStage.QUALIFICATION,
                    reason="Pitch is done and the lead can be qualified.",
                    metadata={"intent": intent.value},
                )

            return StageDecision(
                current_stage=current_stage,
                next_stage=ConversationStage.PITCH,
                reason="Continue the pitch with the approved script.",
                metadata={"intent": intent.value},
            )

        if current_stage == ConversationStage.OBJECTION:
            if objections_open:
                return StageDecision(
                    current_stage=current_stage,
                    next_stage=ConversationStage.OBJECTION,
                    reason="Continue resolving the open objection.",
                    metadata={
                        "objections_open": objections_open,
                        "objections_resolved": objections_resolved,
                    },
                )

            if lead_ready or intent == LeadIntent.READY:
                return StageDecision(
                    current_stage=current_stage,
                    next_stage=ConversationStage.CLOSING,
                    reason="Objection resolved and lead is ready.",
                    metadata={"intent": intent.value},
                )

            return StageDecision(
                current_stage=current_stage,
                next_stage=ConversationStage.QUALIFICATION,
                reason="Objection handled; move into qualification.",
                metadata={"intent": intent.value},
            )

        if current_stage == ConversationStage.QUALIFICATION:
            if lead_ready or intent == LeadIntent.READY:
                return StageDecision(
                    current_stage=current_stage,
                    next_stage=ConversationStage.CLOSING,
                    reason="Qualification signals indicate readiness.",
                    metadata={"intent": intent.value},
                )

            if objections_open:
                return StageDecision(
                    current_stage=current_stage,
                    next_stage=ConversationStage.OBJECTION,
                    reason="A new objection appeared during qualification.",
                    metadata={"objections_open": objections_open},
                )

            return StageDecision(
                current_stage=current_stage,
                next_stage=ConversationStage.QUALIFICATION,
                reason="Continue qualification with the lead.",
                metadata={"intent": intent.value},
            )

        if current_stage == ConversationStage.CLOSING:
            if classification.lower() == "hot" or total_score >= 75:
                return StageDecision(
                    current_stage=current_stage,
                    next_stage=ConversationStage.HANDOFF,
                    reason="Lead is hot and should be handed off.",
                    should_handoff=True,
                    should_follow_up=False,
                    should_continue=False,
                    metadata={
                        "classification": classification,
                        "total_score": total_score,
                    },
                )

            if classification.lower() == "warm" or 40 <= total_score < 75:
                return StageDecision(
                    current_stage=current_stage,
                    next_stage=ConversationStage.FOLLOW_UP,
                    reason="Lead is warm and should receive follow-up.",
                    should_handoff=False,
                    should_follow_up=True,
                    should_continue=False,
                    metadata={
                        "classification": classification,
                        "total_score": total_score,
                    },
                )

            return StageDecision(
                current_stage=current_stage,
                next_stage=ConversationStage.FOLLOW_UP,
                reason="Closing attempted; store for later nurture.",
                should_handoff=False,
                should_follow_up=True,
                should_continue=False,
                metadata={
                    "classification": classification,
                    "total_score": total_score,
                },
            )

        if current_stage == ConversationStage.HANDOFF:
            return StageDecision(
                current_stage=current_stage,
                next_stage=ConversationStage.FOLLOW_UP,
                reason="Handoff completed; follow-up state recorded.",
                should_handoff=False,
                should_follow_up=True,
                should_continue=False,
            )

        if current_stage == ConversationStage.FOLLOW_UP:
            return StageDecision(
                current_stage=current_stage,
                next_stage=ConversationStage.FOLLOW_UP,
                reason="Follow-up state retained for next contact.",
                should_continue=False,
            )

        return StageDecision(
            current_stage=current_stage,
            next_stage=current_stage,
            reason="No stage change applied.",
        )

    def apply_transition(
        self,
        context: ConversationContext,
        decision: StageDecision,
    ) -> ConversationContext:
        """
        Mutates and returns the same context object for convenience.
        The orchestrator can persist this updated state after each turn.
        """
        if self.is_valid_transition(context.stage, decision.next_stage):
            context.stage = decision.next_stage

        context.flags.update(decision.metadata or {})
        context.flags["should_handoff"] = decision.should_handoff
        context.flags["should_follow_up"] = decision.should_follow_up
        context.flags["should_continue"] = decision.should_continue
        return context

    def reset_for_new_call(self) -> ConversationContext:
        """
        Create a clean context for a new call session.
        Long-term memory is handled by memory_manager.py.
        """
        return ConversationContext(stage=ConversationStage.INTRO)

    def stage_needs_retrieval(self, stage: ConversationStage) -> bool:
        """
        Helpful hint for the orchestrator:
        retrieval is usually needed for pitch, objection, qualification, and closing.
        """
        return stage in {
            ConversationStage.PITCH,
            ConversationStage.OBJECTION,
            ConversationStage.QUALIFICATION,
            ConversationStage.CLOSING,
        }

    def stage_needs_handoff(self, stage: ConversationStage, classification: str, total_score: float) -> bool:
        return stage == ConversationStage.HANDOFF or classification.lower() == "hot" or total_score >= 75

    def stage_needs_follow_up(self, stage: ConversationStage, classification: str, total_score: float) -> bool:
        return stage == ConversationStage.FOLLOW_UP or classification.lower() == "warm" or (40 <= total_score < 75)

    def normalize_stage(self, stage_value: str) -> ConversationStage:
        """
        Safe stage conversion for values coming from DB or LLM outputs.
        """
        value = (stage_value or "").strip().lower()
        for stage in ConversationStage:
            if stage.value == value:
                return stage
        return ConversationStage.INTRO

    def normalize_intent(self, intent_value: str) -> LeadIntent:
        """
        Safe intent conversion for values coming from intent detector outputs.
        """
        value = (intent_value or "").strip().lower()
        for intent in LeadIntent:
            if intent.value == value:
                return intent
        return LeadIntent.UNKNOWN

    def should_repeat_pitch(
        self,
        current_stage: ConversationStage,
        objections_open: Optional[List[str]] = None,
        lead_ready: bool = False,
    ) -> bool:
        """
        Returns whether the orchestrator should keep the call in pitch mode.
        """
        objections_open = objections_open or []
        if current_stage == ConversationStage.PITCH and not objections_open and not lead_ready:
            return True
        return False