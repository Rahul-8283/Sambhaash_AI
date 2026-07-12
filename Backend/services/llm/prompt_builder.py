# services/llm/prompt_builder.py

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional, Sequence

from .state_machine import ConversationStage, LeadIntent


@dataclass
class PromptBundle:
    """
    Structured prompt package returned by PromptBuilder.

    This keeps orchestration clean:
    - system_prompt: base behavior and constraints
    - user_prompt: current turn + memory + retrieval context
    - response_format: strict JSON contract for the LLM
    - metadata: useful for debugging / logging
    """
    system_prompt: str
    user_prompt: str
    response_format: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PromptBuilder:
    """
    Builds prompts for the core LLM orchestration layer.

    This file stays aligned with the original plan:
    - use conversation stage
    - use memory snapshot
    - use retrieved Appendix A context
    - keep multilingual behavior natural
    - keep objection handling contextual
    - output strict structured JSON

    The orchestrator should pass the resulting prompt bundle to the model client
    without adding extra free-form instructions.
    """

    def __init__(
        self,
        assistant_name: str = "Sambhaash AI",
        product_name: str = "Rupeezy Partner Program",
        brand_name: str = "Rupeezy",
        max_recent_turns: int = 6,
    ) -> None:
        self.assistant_name = assistant_name
        self.product_name = product_name
        self.brand_name = brand_name
        self.max_recent_turns = max(1, max_recent_turns)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_bundle(
        self,
        user_text: str,
        stage: ConversationStage | str,
        language: Optional[str] = None,
        memory_snapshot: Optional[Dict[str, Any]] = None,
        retrieved_context: Optional[Sequence[Dict[str, Any] | str]] = None,
        intent: Optional[LeadIntent | str] = None,
        objection_type: Optional[str] = None,
        lead_profile: Optional[Dict[str, Any]] = None,
        score: Optional[float] = None,
        classification: Optional[str] = None,
    ) -> PromptBundle:
        """
        Main entry point used by orchestrator.py.

        Returns a complete prompt bundle for the response-generation LLM.
        """
        memory_snapshot = memory_snapshot or {}
        retrieved_context = list(retrieved_context or [])

        normalized_stage = self._normalize_stage(stage)
        normalized_intent = self._normalize_intent(intent)
        normalized_language = self._normalize_language(language)
        normalized_objection = self._normalize_objection(objection_type)

        merged_memory = dict(memory_snapshot)
        if lead_profile:
            merged_memory.setdefault("lead_profile", {}).update(lead_profile)
        if score is not None:
            merged_memory["last_score"] = score
        if classification is not None:
            merged_memory["current_classification"] = classification

        system_prompt = self.build_system_prompt(
            stage=normalized_stage,
            language=normalized_language,
            memory_snapshot=merged_memory,
            intent=normalized_intent,
            objection_type=normalized_objection,
        )

        user_prompt = self.build_user_prompt(
            user_text=user_text,
            stage=normalized_stage,
            language=normalized_language,
            memory_snapshot=merged_memory,
            retrieved_context=retrieved_context,
            intent=normalized_intent,
            objection_type=normalized_objection,
        )

        response_format = self.build_response_format()

        metadata = {
            "assistant_name": self.assistant_name,
            "product_name": self.product_name,
            "brand_name": self.brand_name,
            "stage": normalized_stage,
            "language": normalized_language,
            "intent": normalized_intent,
            "objection_type": normalized_objection,
        }

        return PromptBundle(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_format=response_format,
            metadata=metadata,
        )

    def build_messages(
        self,
        user_text: str,
        stage: ConversationStage | str,
        language: Optional[str] = None,
        memory_snapshot: Optional[Dict[str, Any]] = None,
        retrieved_context: Optional[Sequence[Dict[str, Any] | str]] = None,
        intent: Optional[LeadIntent | str] = None,
        objection_type: Optional[str] = None,
        lead_profile: Optional[Dict[str, Any]] = None,
        score: Optional[float] = None,
        classification: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """
        Returns chat-style messages for providers that use a messages API.
        """
        bundle = self.build_bundle(
            user_text=user_text,
            stage=stage,
            language=language,
            memory_snapshot=memory_snapshot,
            retrieved_context=retrieved_context,
            intent=intent,
            objection_type=objection_type,
            lead_profile=lead_profile,
            score=score,
            classification=classification,
        )
        return [
            {"role": "system", "content": bundle.system_prompt},
            {"role": "user", "content": bundle.user_prompt},
        ]

    def build_full_prompt(
        self,
        user_text: str,
        stage: ConversationStage | str,
        language: Optional[str] = None,
        memory_snapshot: Optional[Dict[str, Any]] = None,
        retrieved_context: Optional[Sequence[Dict[str, Any] | str]] = None,
        intent: Optional[LeadIntent | str] = None,
        objection_type: Optional[str] = None,
        lead_profile: Optional[Dict[str, Any]] = None,
        score: Optional[float] = None,
        classification: Optional[str] = None,
    ) -> str:
        """
        Returns a single concatenated prompt for providers that accept raw text.
        """
        bundle = self.build_bundle(
            user_text=user_text,
            stage=stage,
            language=language,
            memory_snapshot=memory_snapshot,
            retrieved_context=retrieved_context,
            intent=intent,
            objection_type=objection_type,
            lead_profile=lead_profile,
            score=score,
            classification=classification,
        )
        return f"{bundle.system_prompt}\n\n{bundle.user_prompt}\n\n{bundle.response_format}"

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

    def build_system_prompt(
        self,
        stage: str,
        language: str,
        memory_snapshot: Dict[str, Any],
        intent: str,
        objection_type: Optional[str],
    ) -> str:
        """
        Core system prompt that governs model behavior.
        """
        memory_block = self._format_memory_section(memory_snapshot)
        stage_block = self._stage_instructions(stage)
        language_block = self._language_instructions(language)
        behavior_block = self._behavior_instructions()
        output_block = self.build_response_format()

        prompt = f"""
You are {self.assistant_name}, the core reasoning engine for a multilingual voice sales agent.

Your job is to help convert leads for the {self.brand_name} {self.product_name}.
You must produce a natural, persuasive, context-aware response that follows the approved script and the current conversation stage.

### PRIMARY OBJECTIVE
- Move the conversation forward calmly and naturally.
- Preserve trust and momentum.
- Follow the approved Rupeezy script and Appendix A knowledge.
- Use only facts present in the memory or retrieved context.
- Never invent unsupported details.

### CURRENT STAGE
{stage}

### DETECTED LANGUAGE
{language}

### DETECTED INTENT
{intent}

### DETECTED OBJECTION
{objection_type or "none"}

### MEMORY
{memory_block}

### BEHAVIOR RULES
{behavior_block}

### LENGTH CONSTRAINT (CRITICAL FOR TELEPHONY)
- Your responses will be spoken by a Text-to-Speech engine.
- To prevent phone call timeouts, your response MUST be extremely short.
- Maximum 2 sentences. Maximum 25 words total.
- Be punchy, conversational, and direct.

### STAGE-SPECIFIC INSTRUCTIONS
{stage_block}

### LANGUAGE INSTRUCTIONS
{language_block}

### RESPONSE CONTRACT
{output_block}
""".strip()

        return prompt

    def build_response_format(self) -> str:
        """
        Strict JSON contract that orchestrator.py can parse reliably.
        """
        return """
Return strict JSON only with this schema:
{
  "reply_text": "string",
  "stage": "intro|pitch|objection|qualification|closing|handoff|follow_up",
  "intent": "curious|interested|hesitant|objection|ready|defer|callback|trust_concern|support_concern|broker_concern|network_concern|unknown",
  "objection_type": "already_with_broker|no_network|support_concern|trust_concern|call_later|null",
  "confidence": 0.0,
  "score_signals": {
    "intent_signal": 0.0,
    "engagement_signal": 0.0,
    "objection_resolution_signal": 0.0,
    "qualification_signal": 0.0,
    "sentiment_signal": 0.0
  },
  "handoff_required": false,
  "whatsapp_required": false,
  "memory_updates": {
    "preferred_language": "string|null",
    "resolved_objections": ["string"],
    "unresolved_objections": ["string"],
    "conversation_summary": "string",
    "turn_summary": "string"
  },
  "call_summary": {
    "topics_covered": ["string"],
    "objections_raised": ["string"],
    "interest_level": "hot|warm|cold",
    "recommended_next_action": "string"
  }
}
Rules:
- Return JSON only.
- No markdown.
- No explanations.
- No extra keys.
- Use the current stage and memory to stay consistent.
- Use only approved facts from memory and retrieved Appendix A context.
- Keep the reply natural and conversational.
""".strip()

    # ------------------------------------------------------------------
    # User prompt
    # ------------------------------------------------------------------

    def build_user_prompt(
        self,
        user_text: str,
        stage: str,
        language: str,
        memory_snapshot: Dict[str, Any],
        retrieved_context: Sequence[Dict[str, Any] | str],
        intent: str,
        objection_type: Optional[str],
    ) -> str:
        """
        Build the user-facing task prompt for the LLM.
        """
        memory_block = self._format_memory_section(memory_snapshot)
        retrieval_block = self._format_retrieved_context(retrieved_context)
        transcript_block = self._format_recent_turns(memory_snapshot)

        prompt = f"""
### LATEST USER UTTERANCE
{user_text}

### CURRENT STAGE
{stage}

### LANGUAGE
{language}

### CURRENT INTENT
{intent}

### OBJECTION TYPE
{objection_type or "none"}

### AVAILABLE MEMORY
{memory_block}

### RECENT TURNS
{transcript_block}

### APPROVED KNOWLEDGE RETRIEVED FROM APPENDIX A / FAQ / SCRIPT
{retrieval_block}

### TASK
Generate the next assistant reply.

Follow these rules:
1. Stay aligned with the current stage.
2. If the user is objecting, use the acknowledge -> reframe -> differentiate -> guide pattern.
3. If the user is ready, move toward closing or handoff.
4. If the user asks to call later, mark follow-up.
5. If the user is warm but not ready, keep the CTA light and preserve continuity.
6. If the user is cold or skeptical, do not pressure.
7. Mirror the user's language style and code-mixing naturally.
8. Use only approved facts from memory and retrieved context.
9. Do not repeat points already resolved in memory.
10. Return strict JSON only in the specified schema.
11. CRITICAL: If the user explicitly says goodbye, thanks you to end the call, or asks to end the call, you MUST set "stage" to "closing" or "handoff" so the call gracefully hangs up.
""".strip()

        return prompt

    # ------------------------------------------------------------------
    # Helpers: memory / context formatting
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

    def _format_recent_turns(self, memory_snapshot: Dict[str, Any]) -> str:
        recent_turns = memory_snapshot.get("recent_turns") or []
        if not recent_turns:
            return "No recent turns."

        lines: List[str] = []
        for turn in recent_turns[-self.max_recent_turns :]:
            if isinstance(turn, dict):
                speaker = str(turn.get("speaker", "user"))
                text = str(turn.get("text", "")).strip()
                stage = str(turn.get("stage", "intro"))
                intent = str(turn.get("intent", "unknown"))
                if text:
                    lines.append(f"- [{speaker} | {stage} | {intent}] {text}")
            else:
                text = str(turn).strip()
                if text:
                    lines.append(f"- {text}")
        return "\n".join(lines).strip() if lines else "No recent turns."

    def _format_retrieved_context(self, retrieved_context: Sequence[Dict[str, Any] | str]) -> str:
        if not retrieved_context:
            return "No retrieved context."

        lines: List[str] = []
        for idx, item in enumerate(retrieved_context, start=1):
            if isinstance(item, dict):
                section = item.get("section_name") or item.get("source_type") or "retrieved"
                text = item.get("text") or item.get("chunk_text") or ""
                text = str(text).strip()
                if text:
                    lines.append(f"[KB {idx}] {section}: {text}")
            else:
                text = str(item).strip()
                if text:
                    lines.append(f"[KB {idx}] {text}")

        return "\n".join(lines).strip() if lines else "No retrieved context."

    # ------------------------------------------------------------------
    # Stage / language behavior blocks
    # ------------------------------------------------------------------

    def _stage_instructions(self, stage: str) -> str:
        stage = self._normalize_stage(stage)

        if stage == ConversationStage.INTRO.value:
            return """
- Open warmly and briefly.
- Establish trust quickly.
- Keep the hook short.
- Do not overload the lead with details.
- If the lead responds in another language, mirror that language.
""".strip()

        if stage == ConversationStage.PITCH.value:
            return """
- Deliver the approved value proposition clearly.
- Focus on the core benefits only:
  zero joining fee, 100% brokerage share, daily payouts.
- Keep the pitch concise and confident.
- Transition naturally into a question or next step.
""".strip()

        if stage == ConversationStage.OBJECTION.value:
            return """
- Address only the current objection.
- Use the pattern: acknowledge -> reframe -> differentiate -> guide.
- Avoid sounding scripted.
- Do not repeat facts already addressed in memory.
- Keep the tone calm and respectful.
""".strip()

        if stage == ConversationStage.QUALIFICATION.value:
            return """
- Ask one or two relevant qualification questions.
- Focus on readiness, existing network, and willingness to onboard.
- Do not interrogate.
- Use the answer to decide whether the lead is hot, warm, or cold.
""".strip()

        if stage == ConversationStage.CLOSING.value:
            return """
- Move toward a clear call to action.
- Make the next step simple.
- If the lead is ready, encourage sign-up or RM handoff.
- If the lead is hesitant, keep the CTA soft.
""".strip()

        if stage == ConversationStage.HANDOFF.value:
            return """
- Provide a concise handoff-ready response.
- Preserve context for the human RM.
- Summarize the lead's intent and objections naturally.
- Keep the message short and actionable.
""".strip()

        if stage == ConversationStage.FOLLOW_UP.value:
            return """
- Keep the tone light and non-pushy.
- Encourage WhatsApp follow-up or later contact.
- Summarize the value quickly.
- Preserve trust and continuity.
""".strip()

        return """
- Stay natural and context-aware.
- Do not break the conversation flow.
- Use only approved facts.
""".strip()

    def _language_instructions(self, language: str) -> str:
        language = self._normalize_language(language)

        if language == "hindi":
            return """
- Respond in Hindi.
- Keep the tone natural, conversational, and respectful.
- Avoid overly formal or robotic Hindi.
- If the user code-mixes, mirror that style gently.
""".strip()

        if language == "hinglish":
            return """
- Respond in Hinglish.
- Keep code-mixing natural and human.
- Do not translate every phrase too literally.
- Match the user's wording style when it sounds natural.
""".strip()

        if language in {"tamil", "telugu", "marathi", "gujarati", "bengali", "kannada"}:
            return f"""
- Respond in {language.capitalize()} if the conversation clearly requires it.
- Keep the message natural and conversational.
- If confidence is low, fall back to simple English rather than forcing a poor translation.
""".strip()

        return """
- Respond in simple, clear English.
- Keep the tone warm, concise, and natural.
- If the user code-mixes, mirror that style.
""".strip()

    def _behavior_instructions(self) -> str:
        return """
- Always sound like a helpful human sales assistant.
- Do not hallucinate facts or invent policy details.
- Use only facts from memory or retrieved knowledge.
- Do not repeat already resolved objections.
- Do not answer multiple objections at once unless the user clearly bundles them.
- Keep responses concise but complete.
- Preserve the approved sales narrative.
- If the lead shows strong buying intent, move the conversation forward.
- If the lead is uncertain, reduce pressure and preserve trust.
- If the lead requests a callback, mark follow-up naturally.
- If the lead is hot, prepare for human RM handoff.
- If the lead is warm, encourage WhatsApp follow-up gently.
- If the lead is cold, remain polite and low-pressure.
- If the user explicitly says goodbye or asks to end the call, you MUST set "stage" to "closing" to force a hang up.
""".strip()

    # ------------------------------------------------------------------
    # Normalizers
    # ------------------------------------------------------------------

    def _normalize_stage(self, stage: ConversationStage | str) -> str:
        if isinstance(stage, ConversationStage):
            return stage.value

        value = str(stage or "").strip().lower()
        valid = {s.value for s in ConversationStage}
        return value if value in valid else ConversationStage.INTRO.value

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

    def _normalize_intent(self, intent: Optional[LeadIntent | str]) -> str:
        if intent is None:
            return "unknown"
        if isinstance(intent, LeadIntent):
            return intent.value
        value = str(intent).strip().lower()
        return value if value else "unknown"

    def _normalize_objection(self, objection_type: Optional[str]) -> Optional[str]:
        value = str(objection_type or "").strip().lower()
        if not value or value in {"null", "none"}:
            return None

        allowed = {
            "already_with_broker",
            "no_network",
            "support_concern",
            "trust_concern",
            "call_later",
        }
        return value if value in allowed else None

    # ------------------------------------------------------------------
    # Export helpers
    # ------------------------------------------------------------------

    def export_bundle(
        self,
        user_text: str,
        stage: ConversationStage | str,
        language: Optional[str] = None,
        memory_snapshot: Optional[Dict[str, Any]] = None,
        retrieved_context: Optional[Sequence[Dict[str, Any] | str]] = None,
        intent: Optional[LeadIntent | str] = None,
        objection_type: Optional[str] = None,
        lead_profile: Optional[Dict[str, Any]] = None,
        score: Optional[float] = None,
        classification: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Convenience wrapper for callers that prefer plain dicts.
        """
        return self.build_bundle(
            user_text=user_text,
            stage=stage,
            language=language,
            memory_snapshot=memory_snapshot,
            retrieved_context=retrieved_context,
            intent=intent,
            objection_type=objection_type,
            lead_profile=lead_profile,
            score=score,
            classification=classification,
        ).to_dict()