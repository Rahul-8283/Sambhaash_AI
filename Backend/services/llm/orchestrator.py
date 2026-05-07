# services/llm/orchestrator.py

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional, Protocol, Sequence, runtime_checkable
from uuid import uuid4

from .intent_detector import IntentDetector
from .memory_manager import LeadMemory, MemoryManager
from .objection_handler import ObjectionHandler
from .prompt_builder import PromptBundle, PromptBuilder
from .rag_engine import RAGEngine
from .state_machine import ConversationStage, LeadIntent, StateMachine


logger = logging.getLogger(__name__)


@runtime_checkable
class LLMCallableProtocol(Protocol):
    """
    Expected shape for the LLM adapter.

    The orchestrator keeps the provider layer outside this file.
    Inject a callable that accepts a PromptBundle and returns raw text.
    """

    def __call__(self, bundle: PromptBundle) -> str:
        ...


@dataclass
class OrchestrationRequest:
    lead_id: str
    user_text: str
    language: Optional[str] = None
    lead_profile: Dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None
    current_stage: Optional[str] = None
    current_score: Optional[float] = None
    current_classification: Optional[str] = None
    force_handoff: bool = False
    force_follow_up: bool = False
    top_k_context: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrchestrationResult:
    lead_id: str
    session_id: str
    reply_text: str
    language: str
    stage: str
    intent: str
    objection_type: Optional[str]
    confidence: float
    score_signals: Dict[str, float]
    handoff_required: bool
    whatsapp_required: bool
    lead_score: float
    lead_classification: str
    memory_updates: Dict[str, Any]
    call_summary: Dict[str, Any]
    raw_llm_output: Optional[Dict[str, Any]] = None
    raw_llm_text: Optional[str] = None
    retrieved_context: List[Dict[str, Any]] = field(default_factory=list)
    objection_plan: Dict[str, Any] = field(default_factory=dict)
    prompt_bundle: Optional[Dict[str, Any]] = None
    parsed_ok: bool = True
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class Orchestrator:
    """
    Core brain of Sambhaash AI.

    Responsibilities:
    - load/update lead memory
    - detect intent and objections
    - maintain conversation stage
    - retrieve grounded Appendix A context
    - build prompts for the LLM
    - parse structured output
    - update memory with the result
    - emit handoff / WhatsApp / summary signals

    This file intentionally does not:
    - do telephony
    - do STT
    - do TTS
    - calculate scoring math
    - write directly to DB tables

    Those remain in their respective layers.
    """

    def __init__(
        self,
        state_machine: Optional[StateMachine] = None,
        memory_manager: Optional[MemoryManager] = None,
        intent_detector: Optional[IntentDetector] = None,
        objection_handler: Optional[ObjectionHandler] = None,
        rag_engine: Optional[RAGEngine] = None,
        prompt_builder: Optional[PromptBuilder] = None,
        llm_callable: Optional[LLMCallableProtocol] = None,
        model_name: str = "model name",
        api_key: str = "your api key",
    ) -> None:
        self.state_machine = state_machine or StateMachine()
        self.memory_manager = memory_manager or MemoryManager()
        self.intent_detector = intent_detector or IntentDetector(
            model_name=model_name, 
            api_key=api_key,
            llm_callable=llm_callable
        )
        self.objection_handler = objection_handler or ObjectionHandler(model_name=model_name, api_key=api_key)
        self.rag_engine = rag_engine or RAGEngine(model_name=model_name, api_key=api_key)
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.llm_callable = llm_callable
        self.model_name = model_name
        self.api_key = api_key

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_turn(self, request: OrchestrationRequest) -> OrchestrationResult:
        """
        Main entry point for one user utterance.
        """
        lead_id = self._clean_text(request.lead_id)
        user_text = self._clean_text(request.user_text)

        if not lead_id:
            raise ValueError("lead_id is required")
        if not user_text:
            raise ValueError("user_text is required")

        memory = self.memory_manager.get_or_create(lead_id=lead_id, lead_profile=request.lead_profile)
        if request.session_id:
            self.memory_manager.set_session_id(memory, request.session_id)
        elif not memory.last_session_id:
            self.memory_manager.set_session_id(memory, str(uuid4()))

        if request.lead_profile:
            self.memory_manager.update_lead_profile(memory, request.lead_profile)

        if request.language:
            self.memory_manager.set_preferred_language(memory, request.language)

        current_language = request.language or memory.preferred_language or "english"
        current_stage = self._normalize_stage(request.current_stage or memory.conversation_stage)
        current_score = float(request.current_score if request.current_score is not None else memory.last_score)
        current_classification = (
            self._normalize_classification(request.current_classification)
            or memory.current_classification
        )

        # Snapshot before turn processing for intent detection and retrieval.
        snapshot_before = self.memory_manager.ready_for_prompt(memory)

        detected = self.intent_detector.detect(
            user_text=user_text,
            language=current_language,
            memory_snapshot=snapshot_before,
        )

        detected_intent = self._normalize_intent(detected.get("intent"))
        detected_objection = self._normalize_objection_type(detected.get("objection_type"))
        detected_confidence = self._safe_float(detected.get("confidence"), default=0.0)

        # Update memory with the user's turn first.
        self.memory_manager.add_user_turn(
            memory=memory,
            text=user_text,
            language=current_language,
            stage=current_stage,
            intent=detected_intent,
            objection_type=detected_objection,
            score_after_turn=current_score,
        )

        if detected_objection:
            self.memory_manager.add_objection(memory, detected_objection)

        if bool(detected.get("is_callback")) or detected_objection == "call_later":
            self.memory_manager.add_objection(memory, "call_later")

        if bool(detected.get("is_ready")):
            self.memory_manager.update_lead_profile(memory, {"lead_ready": True})

        # Determine the next stage using the original plan.
        decision = self.state_machine.determine_stage(
            current_stage=self.state_machine.normalize_stage(current_stage),
            intent=self.state_machine.normalize_intent(detected_intent),
            total_score=current_score,
            classification=current_classification,
            objections_open=self.memory_manager.get_open_objections(memory),
            objections_resolved=self.memory_manager.get_resolved_objections(memory),
            lead_ready=bool(detected.get("is_ready")),
            asked_to_call_later=bool(detected.get("is_callback")) or detected_objection == "call_later",
            handoff_requested=bool(request.force_handoff),
        )

        if request.force_follow_up:
            decision.should_handoff = False
            decision.should_follow_up = True
            decision.should_continue = False
            decision.next_stage = ConversationStage.FOLLOW_UP

        next_stage = decision.next_stage.value if hasattr(decision.next_stage, "value") else str(decision.next_stage)
        self.memory_manager.set_stage(memory, next_stage)

        # Build the current snapshot after memory and stage updates.
        snapshot_after_update = self.memory_manager.ready_for_prompt(memory)

        # Retrieve grounded context from Appendix A / FAQ / script.
        retrieved_context = self.rag_engine.retrieve(
            query_text=user_text,
            stage=next_stage,
            objection_type=detected_objection,
            language=current_language,
            memory_snapshot=snapshot_after_update,
            top_k=request.top_k_context,
        )
        
        # Merge KB Context from Phase 2A if available
        if request.metadata and request.metadata.get("kb_context") and request.metadata.get("kb_available"):
            kb_context = request.metadata.get("kb_context", {})
            kb_formatted = kb_context.get("formatted_context", "")
            
            if kb_formatted:
                # Prepend KB context to retrieved_context for higher priority
                retrieved_context = [kb_formatted] + list(retrieved_context or [])
                logger.info(f"[PHASE2A] KB Context injected ({len(kb_context.get('context_blocks', []))} chunks)")

        # Objection handling plan is used as an approved guidance layer.
        objection_plan: Dict[str, Any] = {}
        if detected_objection or next_stage == ConversationStage.OBJECTION.value:
            objection_plan = self.objection_handler.handle(
                user_text=user_text,
                objection_type=detected_objection,
                stage=next_stage,
                language=current_language,
                memory_snapshot=snapshot_after_update,
                retrieved_context=retrieved_context,
                intent=detected_intent,
            )

        prompt_context = self._merge_retrieval_with_objection_plan(
            retrieved_context=retrieved_context,
            objection_plan=objection_plan,
        )

        # Build the prompt bundle for the LLM.
        bundle = self.prompt_builder.build_bundle(
            user_text=user_text,
            stage=next_stage,
            language=current_language,
            memory_snapshot=snapshot_after_update,
            retrieved_context=prompt_context,
            intent=detected_intent,
            objection_type=detected_objection,
            lead_profile=memory.lead_profile,
            score=current_score,
            classification=current_classification,
        )

        # Call the LLM.
        raw_llm_text = self._call_llm(bundle)
        parsed = self._parse_llm_output(raw_llm_text)

        if parsed is None:
            parsed = self._fallback_structured_output(
                request=request,
                memory=memory,
                detected=detected,
                decision=decision,
                objection_plan=objection_plan,
                next_stage=next_stage,
                language=current_language,
            )
            parsed_ok = False
        else:
            parsed_ok = True

        normalized = self._normalize_llm_output(
            parsed=parsed,
            request=request,
            detected=detected,
            decision=decision,
            objection_plan=objection_plan,
            next_stage=next_stage,
            current_language=current_language,
            current_classification=current_classification,
            current_score=current_score,
        )

        reply_text = normalized["reply_text"]

        # Update memory with assistant turn.
        self.memory_manager.add_assistant_turn(
            memory=memory,
            text=reply_text,
            language=normalized["language"],
            stage=normalized["stage"],
            intent=normalized["intent"],
            score_after_turn=current_score,
        )

        self._apply_memory_updates(memory, normalized.get("memory_updates", {}))
        self._apply_call_summary(memory, normalized.get("call_summary", {}))
        self._apply_objection_resolution(memory, normalized, detected_objection, objection_plan)

        # If the model or stage decision indicates a higher-level action, enforce it.
        if decision.should_handoff or normalized.get("handoff_required"):
            normalized["handoff_required"] = True
            normalized["whatsapp_required"] = False
            normalized["stage"] = ConversationStage.HANDOFF.value

        if decision.should_follow_up or request.force_follow_up:
            if not normalized.get("handoff_required"):
                normalized["whatsapp_required"] = True
                normalized["stage"] = ConversationStage.FOLLOW_UP.value

        # Persist the stage and lightweight classification state.
        self.memory_manager.set_stage(memory, normalized["stage"])
        if normalized.get("lead_classification"):
            self.memory_manager.set_classification(memory, normalized["lead_classification"])

        # Update the lead score only if the upstream scorer already provided one.
        lead_score = self._safe_float(
            normalized.get("lead_score", current_score),
            default=current_score,
        )
        self.memory_manager.set_last_score(memory, lead_score)

        # Save memory.
        self.memory_manager.save(memory)

        final_snapshot = self.memory_manager.ready_for_prompt(memory)

        return OrchestrationResult(
            lead_id=lead_id,
            session_id=memory.last_session_id or request.session_id or str(uuid4()),
            reply_text=reply_text,
            language=normalized["language"],
            stage=normalized["stage"],
            intent=normalized["intent"],
            objection_type=normalized["objection_type"],
            confidence=normalized["confidence"],
            score_signals=normalized["score_signals"],
            handoff_required=normalized["handoff_required"],
            whatsapp_required=normalized["whatsapp_required"],
            lead_score=lead_score,
            lead_classification=normalized["lead_classification"],
            memory_updates=normalized["memory_updates"],
            call_summary=normalized["call_summary"],
            raw_llm_output=parsed,
            raw_llm_text=raw_llm_text,
            retrieved_context=retrieved_context,
            objection_plan=objection_plan,
            prompt_bundle=bundle.to_dict(),
            parsed_ok=parsed_ok,
            error=None if parsed_ok else "LLM output could not be parsed; fallback response used.",
        )
    def summarize_call(
        self,
        lead_id: str,
        transcript: Sequence[Dict[str, Any] | str],
        final_score: Optional[float] = None,
        final_classification: Optional[str] = None,
        next_action: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a post-call summary for the dashboard / RM handoff.
        """
        memory = self.memory_manager.get_or_create(lead_id=lead_id)
        memory_snapshot = self.memory_manager.ready_for_prompt(memory)
        summary_prompt = self.prompt_builder.build_summary_prompt(
            memory_snapshot=memory_snapshot,
            transcript=transcript,
            final_score=final_score,
            final_classification=final_classification,
            next_action=next_action,
        )

        raw_text = self._call_summary_llm(summary_prompt)
        parsed = self._parse_llm_output(raw_text)

        if parsed is None:
            parsed = {
                "duration_summary": "",
                "topics_covered": [],
                "objections_raised": [],
                "interest_score": int(final_score or memory.last_score or 0),
                "lead_classification": self._normalize_classification(final_classification or memory.current_classification),
                "recommended_next_action": next_action or "nurture",
                "one_line_summary": memory.conversation_summary or "",
            }

        summary = {
            "duration_summary": str(parsed.get("duration_summary", "")),
            "topics_covered": self._as_string_list(parsed.get("topics_covered", [])),
            "objections_raised": self._as_string_list(parsed.get("objections_raised", [])),
            "interest_score": int(self._safe_float(parsed.get("interest_score"), default=final_score or memory.last_score or 0)),
            "lead_classification": self._normalize_classification(
                parsed.get("lead_classification", final_classification or memory.current_classification)
            ),
            "recommended_next_action": str(parsed.get("recommended_next_action", next_action or "nurture")),
            "one_line_summary": str(parsed.get("one_line_summary", memory.conversation_summary or "")),
        }

        self.memory_manager.update_summary(
            memory,
            conversation_summary=summary["one_line_summary"],
            full_conversation_summary=summary["one_line_summary"],
        )
        self.memory_manager.record_call_end(
            memory,
            summary=summary["one_line_summary"],
            final_score=summary["interest_score"],
            final_classification=summary["lead_classification"],
        )
        self.memory_manager.save(memory)

        return summary

    # ------------------------------------------------------------------
    # LLM invocation
    # ------------------------------------------------------------------

    def _call_llm(self, bundle: PromptBundle) -> str:
        if self.llm_callable is None:
            raise NotImplementedError(
                "No LLM callable was injected into Orchestrator. "
                "Pass a callable that accepts PromptBundle and returns model text."
            )
        return self.llm_callable(bundle)

    def _call_summary_llm(self, summary_prompt: str) -> str:
        if self.llm_callable is None:
            raise NotImplementedError(
                "No LLM callable was injected into Orchestrator. "
                "Pass a callable that accepts PromptBundle and returns model text."
            )

        bundle = PromptBundle(
            system_prompt="You are the summary generation layer.",
            user_prompt=summary_prompt,
            response_format="Return strict JSON only.",
            metadata={"mode": "summary"},
        )
        return self.llm_callable(bundle)

    # ------------------------------------------------------------------
    # Parsing / normalization
    # ------------------------------------------------------------------

    def _parse_llm_output(self, raw_text: Optional[str]) -> Optional[Dict[str, Any]]:
        if not raw_text:
            return None

        text = str(raw_text).strip()
        if not text:
            return None

        data = self._safe_json_loads(text)
        if isinstance(data, dict):
            return data

        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match:
            return self._safe_json_loads(match.group(0))

        return None

    def _safe_json_loads(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            loaded = json.loads(text)
            if isinstance(loaded, dict):
                return loaded
            return None
        except Exception:
            return None

    def _normalize_llm_output(
        self,
        parsed: Dict[str, Any],
        request: OrchestrationRequest,
        detected: Dict[str, Any],
        decision: Any,
        objection_plan: Dict[str, Any],
        next_stage: str,
        current_language: str,
        current_classification: str,
        current_score: float,
    ) -> Dict[str, Any]:
        reply_text = self._clean_text(parsed.get("reply_text") or "")
        if not reply_text:
            reply_text = self._fallback_reply(
                request=request,
                detected=detected,
                decision=decision,
                objection_plan=objection_plan,
                next_stage=next_stage,
                language=current_language,
            )

        stage = self._normalize_stage(parsed.get("stage") or next_stage)
        intent = self._normalize_intent(parsed.get("intent") or detected.get("intent"))
        objection_type = self._normalize_objection_type(parsed.get("objection_type") or detected.get("objection_type"))
        confidence = self._clamp_float(parsed.get("confidence", detected.get("confidence", 0.0)), 0.0, 1.0)

        score_signals = self._normalize_score_signals(parsed.get("score_signals", {}))

        memory_updates = parsed.get("memory_updates") or {}
        if not isinstance(memory_updates, dict):
            memory_updates = {}

        call_summary = parsed.get("call_summary") or {}
        if not isinstance(call_summary, dict):
            call_summary = {}

        handoff_required = bool(parsed.get("handoff_required", False))
        whatsapp_required = bool(parsed.get("whatsapp_required", False))

        lead_classification = self._normalize_classification(
            call_summary.get("lead_classification")
            or memory_updates.get("lead_classification")
            or current_classification
        )

        lead_score = self._safe_float(
            parsed.get("lead_score", current_score),
            default=current_score,
        )

        return {
            "reply_text": reply_text,
            "stage": stage,
            "intent": intent,
            "objection_type": objection_type,
            "confidence": confidence,
            "score_signals": score_signals,
            "handoff_required": handoff_required,
            "whatsapp_required": whatsapp_required,
            "memory_updates": self._normalize_memory_updates(memory_updates),
            "call_summary": self._normalize_call_summary(call_summary, lead_classification, current_score),
            "lead_score": lead_score,
            "lead_classification": lead_classification,
            "language": self._normalize_language(parsed.get("language") or current_language),
        }

    # ------------------------------------------------------------------
    # Fallbacks
    # ------------------------------------------------------------------

    def _fallback_structured_output(
        self,
        request: OrchestrationRequest,
        memory: LeadMemory,
        detected: Dict[str, Any],
        decision: Any,
        objection_plan: Dict[str, Any],
        next_stage: str,
        language: str,
    ) -> Dict[str, Any]:
        reply_text = self._fallback_reply(
            request=request,
            detected=detected,
            decision=decision,
            objection_plan=objection_plan,
            next_stage=next_stage,
            language=language,
        )

        current_classification = self._normalize_classification(memory.current_classification)
        current_score = self._safe_float(memory.last_score, default=0.0)

        return {
            "reply_text": reply_text,
            "stage": next_stage,
            "intent": self._normalize_intent(detected.get("intent")),
            "objection_type": self._normalize_objection_type(detected.get("objection_type")),
            "confidence": self._clamp_float(detected.get("confidence", 0.0), 0.0, 1.0),
            "score_signals": {
                "intent_signal": 0.0,
                "engagement_signal": 0.0,
                "objection_resolution_signal": 0.0,
                "qualification_signal": 0.0,
                "sentiment_signal": 0.0,
            },
            "handoff_required": bool(decision.should_handoff),
            "whatsapp_required": bool(decision.should_follow_up),
            "memory_updates": {
                "preferred_language": self._normalize_language(language),
                "resolved_objections": [],
                "unresolved_objections": [self._normalize_objection_type(detected.get("objection_type"))]
                if self._normalize_objection_type(detected.get("objection_type"))
                else [],
                "conversation_summary": memory.conversation_summary,
                "turn_summary": self._clean_text(request.user_text),
            },
            "call_summary": {
                "topics_covered": [],
                "objections_raised": [self._normalize_objection_type(detected.get("objection_type"))]
                if self._normalize_objection_type(detected.get("objection_type"))
                else [],
                "interest_level": current_classification,
                "recommended_next_action": "handoff" if decision.should_handoff else "follow_up" if decision.should_follow_up else "continue",
            },
            "lead_score": current_score,
            "lead_classification": current_classification,
            "language": self._normalize_language(language),
        }

    def _fallback_reply(
        self,
        request: OrchestrationRequest,
        detected: Dict[str, Any],
        decision: Any,
        objection_plan: Dict[str, Any],
        next_stage: str,
        language: str,
    ) -> str:
        objection_type = self._normalize_objection_type(detected.get("objection_type"))
        intent = self._normalize_intent(detected.get("intent"))

        if objection_plan and objection_plan.get("response_text"):
            return self._clean_text(str(objection_plan["response_text"]))

        if objection_type == "call_later" or request.force_follow_up:
            return self._language_safe_reply(
                language,
                "No problem — I will keep this short and follow up later with the key details.",
            )

        if objection_type == "already_with_broker":
            return self._language_safe_reply(
                language,
                "That makes sense. The main question is whether your current setup gives you better economics and smoother payouts.",
            )

        if objection_type == "no_network":
            return self._language_safe_reply(
                language,
                "That is okay. Even a small but relevant client base can be enough to begin, and the program is designed to help partners grow over time.",
            )

        if objection_type == "support_concern":
            return self._language_safe_reply(
                language,
                "That is a very valid concern. Support matters, and I can walk you through how the official onboarding flow handles it.",
            )

        if objection_type == "trust_concern":
            return self._language_safe_reply(
                language,
                "I understand — trust is important before moving forward. I can quickly summarize the official details so you can evaluate them clearly.",
            )

        if bool(detected.get("is_ready")) or intent == "ready":
            return self._language_safe_reply(
                language,
                "Great — I will keep this simple and help with the next step.",
            )

        if next_stage == ConversationStage.PITCH.value:
            return self._language_safe_reply(
                language,
                "Let me quickly share the main benefits and then we can see if it makes sense for you.",
            )

        if next_stage == ConversationStage.QUALIFICATION.value:
            return self._language_safe_reply(
                language,
                "Let me ask one quick question so I can guide this correctly.",
            )

        if next_stage == ConversationStage.HANDOFF.value:
            return self._language_safe_reply(
                language,
                "I will share your context with the relationship manager so the next step is smooth.",
            )

        return self._language_safe_reply(
            language,
            "Understood. Let us continue in the most useful way from here.",
        )

    def _language_safe_reply(self, language: str, text: str) -> str:
        """
        Keep the fallback safe and natural without over-translating.
        """
        return self._clean_text(text)

    # ------------------------------------------------------------------
    # Memory helpers
    # ------------------------------------------------------------------

    def _apply_memory_updates(self, memory: LeadMemory, memory_updates: Dict[str, Any]) -> None:
        if not memory_updates:
            return

        preferred_language = memory_updates.get("preferred_language")
        if preferred_language:
            self.memory_manager.set_preferred_language(memory, preferred_language)

        for objection in memory_updates.get("resolved_objections", []) or []:
            self.memory_manager.resolve_objection(memory, objection)

        for objection in memory_updates.get("unresolved_objections", []) or []:
            self.memory_manager.mark_objection_unresolved(memory, objection)

        conversation_summary = memory_updates.get("conversation_summary")
        if conversation_summary:
            self.memory_manager.update_summary(memory, conversation_summary=conversation_summary)

        turn_summary = memory_updates.get("turn_summary")
        if turn_summary:
            self.memory_manager.append_summary_line(memory, turn_summary)

    def _apply_call_summary(self, memory: LeadMemory, call_summary: Dict[str, Any]) -> None:
        if not call_summary:
            return

        one_line = call_summary.get("one_line_summary")
        if one_line:
            self.memory_manager.update_summary(memory, conversation_summary=str(one_line))

        classification = call_summary.get("interest_level") or call_summary.get("lead_classification")
        if classification:
            self.memory_manager.set_classification(memory, str(classification))

    def _apply_objection_resolution(
        self,
        memory: LeadMemory,
        normalized: Dict[str, Any],
        detected_objection: Optional[str],
        objection_plan: Dict[str, Any],
    ) -> None:
        if not detected_objection:
            return

        if bool(objection_plan.get("resolved")) or normalized["stage"] in {ConversationStage.CLOSING.value, ConversationStage.HANDOFF.value}:
            self.memory_manager.resolve_objection(memory, detected_objection)

    # ------------------------------------------------------------------
    # Merge / context helpers
    # ------------------------------------------------------------------

    def _merge_retrieval_with_objection_plan(
        self,
        retrieved_context: List[Dict[str, Any]],
        objection_plan: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        merged = list(retrieved_context or [])

        if objection_plan and objection_plan.get("response_text"):
            merged.insert(
                0,
                {
                    "section_name": "Approved objection guidance",
                    "source_type": "objection_plan",
                    "text": str(objection_plan.get("response_text", "")),
                    "metadata": {
                        "objection_type": objection_plan.get("objection_type"),
                        "confidence": objection_plan.get("confidence", 0.0),
                    },
                },
            )
        return merged

    # ------------------------------------------------------------------
    # Normalization utilities
    # ------------------------------------------------------------------

    def _normalize_stage(self, stage: Optional[str]) -> str:
        value = str(stage or "").strip().lower()
        valid = {s.value for s in ConversationStage}
        return value if value in valid else ConversationStage.INTRO.value

    def _normalize_intent(self, intent: Optional[str]) -> str:
        value = str(intent or "").strip().lower()
        valid = {i.value for i in LeadIntent}
        return value if value in valid else "unknown"

    def _normalize_objection_type(self, objection_type: Optional[str]) -> Optional[str]:
        value = str(objection_type or "").strip().lower()
        if not value or value in {"none", "null"}:
            return None
        allowed = {
            "already_with_broker",
            "no_network",
            "support_concern",
            "trust_concern",
            "call_later",
        }
        return value if value in allowed else None

    def _normalize_language(self, language: Optional[str]) -> str:
        value = str(language or "english").strip().lower()
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
        return value if value in allowed else "english"

    def _normalize_classification(self, classification: Optional[str]) -> str:
        value = str(classification or "").strip().lower()
        if value in {"hot", "warm", "cold"}:
            return value
        return "cold"

    def _normalize_score_signals(self, score_signals: Any) -> Dict[str, float]:
        default = {
            "intent_signal": 0.0,
            "engagement_signal": 0.0,
            "objection_resolution_signal": 0.0,
            "qualification_signal": 0.0,
            "sentiment_signal": 0.0,
        }
        if not isinstance(score_signals, dict):
            return default

        for key in default.keys():
            default[key] = self._clamp_float(score_signals.get(key, 0.0), 0.0, 1.0)
        return default

    def _normalize_memory_updates(self, memory_updates: Any) -> Dict[str, Any]:
        if not isinstance(memory_updates, dict):
            return {
                "preferred_language": None,
                "resolved_objections": [],
                "unresolved_objections": [],
                "conversation_summary": "",
                "turn_summary": "",
            }

        return {
            "preferred_language": memory_updates.get("preferred_language"),
            "resolved_objections": self._as_string_list(memory_updates.get("resolved_objections", [])),
            "unresolved_objections": self._as_string_list(memory_updates.get("unresolved_objections", [])),
            "conversation_summary": str(memory_updates.get("conversation_summary", "") or ""),
            "turn_summary": str(memory_updates.get("turn_summary", "") or ""),
        }

    def _normalize_call_summary(self, call_summary: Any, classification: str, score: float) -> Dict[str, Any]:
        if not isinstance(call_summary, dict):
            return {
                "topics_covered": [],
                "objections_raised": [],
                "interest_level": classification,
                "recommended_next_action": "continue",
                "one_line_summary": "",
            }

        return {
            "topics_covered": self._as_string_list(call_summary.get("topics_covered", [])),
            "objections_raised": self._as_string_list(call_summary.get("objections_raised", [])),
            "interest_level": self._normalize_classification(call_summary.get("interest_level", classification)),
            "recommended_next_action": str(call_summary.get("recommended_next_action", "continue") or "continue"),
            "one_line_summary": str(call_summary.get("one_line_summary", "") or ""),
        }

    def _as_string_list(self, value: Any) -> List[str]:
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        if value is None:
            return []
        if isinstance(value, str):
            return [value] if value.strip() else []
        return [str(value)]

    # ------------------------------------------------------------------
    # Float / text helpers
    # ------------------------------------------------------------------

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return default

    def _clamp_float(self, value: Any, min_value: float, max_value: float) -> float:
        try:
            f = float(value)
        except Exception:
            f = min_value
        return max(min_value, min(max_value, f))

    def _clean_text(self, value: Optional[str]) -> str:
        return re.sub(r"\s+", " ", (value or "").strip())

    # ------------------------------------------------------------------
    # Call state helpers
    # ------------------------------------------------------------------

    def start_new_session(
        self,
        lead_id: str,
        lead_profile: Optional[Dict[str, Any]] = None,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Initialize or reset a call session while preserving long-term memory.
        """
        memory = self.memory_manager.reset_session_state(lead_id=lead_id)
        if lead_profile:
            self.memory_manager.update_lead_profile(memory, lead_profile)
        if language:
            self.memory_manager.set_preferred_language(memory, language)
        self.memory_manager.save(memory)
        return self.memory_manager.ready_for_prompt(memory)

    def get_memory_snapshot(self, lead_id: str) -> Optional[Dict[str, Any]]:
        memory = self.memory_manager.load(lead_id)
        if memory is None:
            return None
        return self.memory_manager.ready_for_prompt(memory)

    def build_prompt_preview(
        self,
        lead_id: str,
        user_text: str,
        language: Optional[str] = None,
        top_k_context: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Useful for debugging and demos.
        """
        memory = self.memory_manager.get_or_create(lead_id=lead_id)
        snapshot = self.memory_manager.ready_for_prompt(memory)
        retrieved_context = self.rag_engine.retrieve(
            query_text=user_text,
            stage=snapshot.get("stage") or memory.conversation_stage,
            objection_type=None,
            language=language or snapshot.get("preferred_language"),
            memory_snapshot=snapshot,
            top_k=top_k_context,
        )

        bundle = self.prompt_builder.build_bundle(
            user_text=user_text,
            stage=snapshot.get("stage") or memory.conversation_stage,
            language=language or snapshot.get("preferred_language"),
            memory_snapshot=snapshot,
            retrieved_context=retrieved_context,
            intent="unknown",
            objection_type=None,
            lead_profile=memory.lead_profile,
            score=memory.last_score,
            classification=memory.current_classification,
        )

        return bundle.to_dict()