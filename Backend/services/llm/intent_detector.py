# services/llm/intent_detector.py

from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Any, Dict, Optional, Tuple


class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class ObjectionType(str, Enum):
    ALREADY_WITH_BROKER = "already_with_broker"
    NO_NETWORK = "no_network"
    SUPPORT_CONCERN = "support_concern"
    TRUST_CONCERN = "trust_concern"
    CALL_LATER = "call_later"
    NONE = "null"


@dataclass
class QualificationSignals:
    has_existing_clients: bool = False
    profession: str = "unknown"
    asks_about_payouts: bool = False
    asks_about_onboarding: bool = False


@dataclass
class IntentDetectionResult:
    intent: str = "unknown"
    confidence: float = 0.0
    is_objection: bool = False
    objection_type: Optional[str] = None
    is_ready: bool = False
    is_callback: bool = False
    sentiment: str = "neutral"
    qualification_signals: QualificationSignals = field(default_factory=QualificationSignals)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        # Keep objection_type null instead of string "null"
        if payload.get("objection_type") == "null":
            payload["objection_type"] = None
        return payload


class IntentDetector:
    """
    Detects user intent, objections, sentiment, and qualification signals.

    This module is intentionally designed to orchestrate cleanly with:
    - state_machine.py
    - memory_manager.py
    - rag_engine.py
    - prompt_builder.py
    - orchestrator.py

    It returns a strict structured object so downstream layers do not need
    to guess what the user meant.
    """

    VALID_INTENTS = {
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

    def __init__(
        self,
        model_name: str = "model name",
        api_key: str = "your api key",
        llm_callable: Optional[Any] = None,
    ) -> None:
        self.model_name = model_name
        self.api_key = api_key
        self.llm_callable = llm_callable

    def detect(
        self,
        user_text: str,
        language: Optional[str] = None,
        memory_snapshot: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Main entry point used by orchestrator.py

        Priority:
        1. Try LLM-based structured detection
        2. Parse and sanitize output
        3. Fall back to deterministic heuristics if needed
        """
        user_text = self._clean_text(user_text)

        if not user_text:
            result = IntentDetectionResult()
            return result.to_dict()

        prompt = self._build_prompt(
            user_text=user_text,
            language=language,
            memory_snapshot=memory_snapshot,
        )

        raw_response = self._call_llm(prompt)
        parsed = self._parse_response(raw_response)

        if parsed is not None:
            return parsed

        fallback = self._heuristic_detect(user_text=user_text, language=language, memory_snapshot=memory_snapshot)
        return fallback.to_dict()

    # ------------------------------------------------------------------
    # Prompting
    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        user_text: str,
        language: Optional[str],
        memory_snapshot: Optional[Dict[str, Any]],
    ) -> str:
        memory_context = json.dumps(memory_snapshot or {}, ensure_ascii=False, indent=2)

        prompt = f"""
You are an intent detection module for a multilingual sales-call orchestration system.

Your job is to analyze the latest user utterance and return ONLY strict JSON.

You must detect:
- intent
- confidence
- whether the utterance is an objection
- objection type
- readiness
- callback / deferral signals
- sentiment
- qualification signals

### Conversation context
Detected language: {language or "unknown"}

### Memory snapshot
{memory_context}

### Latest user utterance
{user_text}

### Allowed intent values
- curious
- interested
- hesitant
- objection
- ready
- defer
- callback
- trust_concern
- support_concern
- broker_concern
- network_concern
- unknown

### Core objection types
Use exactly one of these if applicable:
- already_with_broker
- no_network
- support_concern
- trust_concern
- call_later

### Sentiment values
- positive
- neutral
- negative

### Qualification signals
Extract these if present:
- has_existing_clients (bool)
- profession (mfd / advisor / insurance / influencer / unknown)
- asks_about_payouts (bool)
- asks_about_onboarding (bool)

### Output JSON schema
{{
  "intent": "curious|interested|hesitant|objection|ready|defer|callback|trust_concern|support_concern|broker_concern|network_concern|unknown",
  "confidence": 0.0,
  "is_objection": true,
  "objection_type": "already_with_broker|no_network|support_concern|trust_concern|call_later|null",
  "is_ready": false,
  "is_callback": false,
  "sentiment": "positive|neutral|negative",
  "qualification_signals": {{
    "has_existing_clients": false,
    "profession": "unknown",
    "asks_about_payouts": false,
    "asks_about_onboarding": false
  }}
}}

Rules:
- Return JSON only.
- Do not add explanations.
- Do not wrap in markdown.
- Prefer the most specific intent.
- If multiple intents exist, choose the dominant one.
- If the message is a deferral, set is_callback true only when they explicitly ask to call later or follow up later.
- If the message expresses a concern about trust, support, broker comparison, or network, mark is_objection true.
""".strip()

        return prompt

    def _call_llm(self, prompt: str) -> str:
        """
        Hook for your actual model client.

        Keep this method as the single place where the model provider is called.
        Replace the placeholder with your chosen LLM integration later.

        The prompt above is already strict enough for structured output.
        """
        if getattr(self, "llm_callable", None):
            from services.llm.prompt_builder import PromptBundle
            bundle = PromptBundle(
                system_prompt="You are an intent detection module for a multilingual sales-call orchestration system.",
                user_prompt=prompt,
                response_format="Return strict JSON only.",
                metadata={"mode": "intent"}
            )
            return self.llm_callable(bundle)

        raise NotImplementedError("LLM client is not wired yet.")

    # ------------------------------------------------------------------
    # Parsing / validation
    # ------------------------------------------------------------------

    def _parse_response(self, raw_response: str) -> Optional[Dict[str, Any]]:
        if not raw_response:
            return None

        text = raw_response.strip()

        # Try direct JSON
        data = self._safe_json_loads(text)
        if data is None:
            # Try extracting a JSON object from surrounding text
            match = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if match:
                data = self._safe_json_loads(match.group(0))

        if data is None:
            return None

        return self._normalize_output(data)

    def _normalize_output(self, data: Dict[str, Any]) -> Dict[str, Any]:
        intent = self._normalize_intent(str(data.get("intent", "unknown")))
        confidence = self._clamp_float(data.get("confidence", 0.0), 0.0, 1.0)

        objection_type = data.get("objection_type", None)
        if objection_type in ("null", "", None):
            objection_type = None
        else:
            objection_type = self._normalize_objection_type(str(objection_type))

        qualification_raw = data.get("qualification_signals", {}) or {}
        qualification = QualificationSignals(
            has_existing_clients=bool(qualification_raw.get("has_existing_clients", False)),
            profession=self._normalize_profession(str(qualification_raw.get("profession", "unknown"))),
            asks_about_payouts=bool(qualification_raw.get("asks_about_payouts", False)),
            asks_about_onboarding=bool(qualification_raw.get("asks_about_onboarding", False)),
        )

        is_objection = bool(data.get("is_objection", False))
        is_ready = bool(data.get("is_ready", False))
        is_callback = bool(data.get("is_callback", False))
        sentiment = self._normalize_sentiment(str(data.get("sentiment", "neutral")))

        # Safety rules to keep output consistent
        if objection_type is not None:
            is_objection = True

        if intent == "ready":
            is_ready = True

        if intent == "callback" or intent == "defer":
            is_callback = True

        result = IntentDetectionResult(
            intent=intent,
            confidence=confidence,
            is_objection=is_objection,
            objection_type=objection_type,
            is_ready=is_ready,
            is_callback=is_callback,
            sentiment=sentiment,
            qualification_signals=qualification,
        )

        return result.to_dict()

    def _safe_json_loads(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            loaded = json.loads(text)
            if isinstance(loaded, dict):
                return loaded
            return None
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Heuristic fallback
    # ------------------------------------------------------------------

    def _heuristic_detect(
        self,
        user_text: str,
        language: Optional[str] = None,
        memory_snapshot: Optional[Dict[str, Any]] = None,
    ) -> IntentDetectionResult:
        text = user_text.lower()

        objection_type = self._heuristic_objection_type(text)
        intent = self._heuristic_intent(text, objection_type)
        sentiment = self._heuristic_sentiment(text)
        qualification = self._heuristic_qualification(text, memory_snapshot)
        confidence = self._heuristic_confidence(intent, objection_type, qualification, text)

        is_objection = objection_type is not None
        is_ready = intent == "ready"
        is_callback = intent == "callback" or objection_type == ObjectionType.CALL_LATER.value

        return IntentDetectionResult(
            intent=intent,
            confidence=confidence,
            is_objection=is_objection,
            objection_type=objection_type,
            is_ready=is_ready,
            is_callback=is_callback,
            sentiment=sentiment,
            qualification_signals=qualification,
        )

    def _heuristic_objection_type(self, text: str) -> Optional[str]:
        if self._contains_any(text, [
            "already have", "already got", "already with", "another broker", "other broker", "broker already",
        ]):
            return ObjectionType.ALREADY_WITH_BROKER.value

        if self._contains_any(text, [
            "no network", "don't have enough contacts", "do not have enough contacts", "no contacts",
            "not enough contacts", "small network", "no clients", "no client base",
        ]):
            return ObjectionType.NO_NETWORK.value

        if self._contains_any(text, [
            "support", "who will support", "who handles support", "client support", "service support",
            "what if my clients face issues", "issues with clients",
        ]):
            return ObjectionType.SUPPORT_CONCERN.value

        if self._contains_any(text, [
            "trust", "trustworthy", "reliable", "safe", "legit", "fraud", "genuine", "authentic",
        ]):
            return ObjectionType.TRUST_CONCERN.value

        if self._contains_any(text, [
            "call me later", "later", "not now", "busy", "another time", "follow up later",
            "sometime later", "think about it",
        ]):
            return ObjectionType.CALL_LATER.value

        return None

    def _heuristic_intent(self, text: str, objection_type: Optional[str]) -> str:
        if objection_type == ObjectionType.CALL_LATER.value:
            return "defer"

        if objection_type in {
            ObjectionType.ALREADY_WITH_BROKER.value,
            ObjectionType.NO_NETWORK.value,
            ObjectionType.SUPPORT_CONCERN.value,
            ObjectionType.TRUST_CONCERN.value,
        }:
            return "objection"

        if self._contains_any(text, [
            "send me", "share the link", "sign me up", "i want to join", "how do i join",
            "register me", "send details", "send the details", "i am ready",
        ]):
            return "ready"

        if self._contains_any(text, [
            "yes", "interested", "sounds good", "tell me more", "how does it work",
            "what is the process", "okay", "ok", "fine",
        ]):
            return "interested"

        if self._contains_any(text, [
            "maybe", "not sure", "confused", "let me think", "thinking", "not now",
        ]):
            return "hesitant"

        if self._contains_any(text, [
            "callback", "call later", "later", "follow up", "talk later",
        ]):
            return "callback"

        return "curious"

    def _heuristic_sentiment(self, text: str) -> str:
        if self._contains_any(text, [
            "great", "good", "nice", "interested", "sure", "yes", "okay", "ok", "sounds good", "perfect",
        ]):
            return Sentiment.POSITIVE.value

        if self._contains_any(text, [
            "no", "not interested", "bad", "wrong", "scam", "useless", "don't want", "do not want",
        ]):
            return Sentiment.NEGATIVE.value

        return Sentiment.NEUTRAL.value

    def _heuristic_qualification(
        self,
        text: str,
        memory_snapshot: Optional[Dict[str, Any]],
    ) -> QualificationSignals:
        has_existing_clients = self._contains_any(text, [
            "clients", "client base", "portfolio", "business", "network", "followers", "subscribers",
        ])

        asks_about_payouts = self._contains_any(text, [
            "payout", "payouts", "brokerage share", "earnings", "income", "commission",
        ])

        asks_about_onboarding = self._contains_any(text, [
            "onboarding", "register", "signup", "sign up", "join", "how to start",
        ])

        profession = "unknown"
        if self._contains_any(text, ["mfd", "mutual fund distributor"]):
            profession = "mfd"
        elif self._contains_any(text, ["advisor", "financial advisor"]):
            profession = "advisor"
        elif self._contains_any(text, ["insurance", "insurance agent"]):
            profession = "insurance"
        elif self._contains_any(text, ["influencer", "creator", "content creator"]):
            profession = "influencer"

        # If memory already indicates a profession, prefer it when user text is ambiguous.
        if profession == "unknown" and memory_snapshot:
            profile = memory_snapshot.get("lead_profile", {}) or {}
            stored_profession = str(profile.get("profession", "")).strip().lower()
            if stored_profession in {"mfd", "advisor", "insurance", "influencer"}:
                profession = stored_profession

        return QualificationSignals(
            has_existing_clients=has_existing_clients,
            profession=profession,
            asks_about_payouts=asks_about_payouts,
            asks_about_onboarding=asks_about_onboarding,
        )

    def _heuristic_confidence(
        self,
        intent: str,
        objection_type: Optional[str],
        qualification: QualificationSignals,
        text: str,
    ) -> float:
        confidence = 0.35

        if intent in {"ready", "objection"}:
            confidence += 0.25
        elif intent in {"interested", "defer", "callback"}:
            confidence += 0.18
        else:
            confidence += 0.08

        if objection_type is not None:
            confidence += 0.15

        if qualification.has_existing_clients:
            confidence += 0.06
        if qualification.asks_about_payouts:
            confidence += 0.05
        if qualification.asks_about_onboarding:
            confidence += 0.05

        if len(text.split()) <= 3:
            confidence -= 0.08

        return self._clamp_float(confidence, 0.0, 0.95)

    # ------------------------------------------------------------------
    # Normalizers
    # ------------------------------------------------------------------

    def _normalize_intent(self, intent: str) -> str:
        value = (intent or "unknown").strip().lower()
        if value not in self.VALID_INTENTS:
            return "unknown"
        return value

    def _normalize_objection_type(self, objection_type: str) -> Optional[str]:
        value = (objection_type or "").strip().lower()
        mapping = {
            "already_with_broker": ObjectionType.ALREADY_WITH_BROKER.value,
            "no_network": ObjectionType.NO_NETWORK.value,
            "support_concern": ObjectionType.SUPPORT_CONCERN.value,
            "trust_concern": ObjectionType.TRUST_CONCERN.value,
            "call_later": ObjectionType.CALL_LATER.value,
            "null": None,
            "none": None,
        }
        if value in mapping:
            return mapping[value]
        return None

    def _normalize_sentiment(self, sentiment: str) -> str:
        value = (sentiment or "neutral").strip().lower()
        if value not in {Sentiment.POSITIVE.value, Sentiment.NEUTRAL.value, Sentiment.NEGATIVE.value}:
            return Sentiment.NEUTRAL.value
        return value

    def _normalize_profession(self, profession: str) -> str:
        value = (profession or "unknown").strip().lower()
        if value in {"mfd", "advisor", "insurance", "influencer"}:
            return value
        return "unknown"

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _clean_text(self, text: Optional[str]) -> str:
        return re.sub(r"\s+", " ", (text or "").strip())

    def _clamp_float(self, value: Any, min_value: float, max_value: float) -> float:
        try:
            f = float(value)
        except Exception:
            f = min_value
        return max(min_value, min(max_value, f))

    def _contains_any(self, text: str, phrases: list[str]) -> bool:
        return any(phrase in text for phrase in phrases)