# services/llm/memory_manager.py

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from uuid import uuid4

from .state_machine import ConversationStage, LeadIntent


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat()


def normalize_text(value: Optional[str]) -> str:
    return (value or "").strip()


def normalize_key(value: Optional[str]) -> str:
    return normalize_text(value).lower()


@runtime_checkable
class MemoryStoreProtocol(Protocol):
    """
    Optional persistence adapter.

    Implement this in your database layer later and inject it into MemoryManager.
    The memory layer stays independent from Supabase / SQLAlchemy specifics.
    """

    def load_lead_memory(self, lead_id: str) -> Optional[Dict[str, Any]]:
        ...

    def save_lead_memory(self, lead_id: str, payload: Dict[str, Any]) -> None:
        ...


@dataclass
class TurnRecord:
    turn_id: str
    speaker: str
    text: str
    language: Optional[str] = None
    stage: str = "intro"
    intent: str = "unknown"
    objection_type: Optional[str] = None
    score_after_turn: float = 0.0
    timestamp: str = field(default_factory=iso_now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TurnRecord":
        return cls(
            turn_id=data.get("turn_id", str(uuid4())),
            speaker=data.get("speaker", "user"),
            text=data.get("text", ""),
            language=data.get("language"),
            stage=data.get("stage", "intro"),
            intent=data.get("intent", "unknown"),
            objection_type=data.get("objection_type"),
            score_after_turn=float(data.get("score_after_turn", 0.0)),
            timestamp=data.get("timestamp", iso_now()),
        )


@dataclass
class ObjectionRecord:
    objection_type: str
    first_raised_at: str = field(default_factory=iso_now)
    last_raised_at: str = field(default_factory=iso_now)
    resolved: bool = False
    resolved_at: Optional[str] = None
    times_raised: int = 1
    resolution_notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ObjectionRecord":
        return cls(
            objection_type=data.get("objection_type", ""),
            first_raised_at=data.get("first_raised_at", iso_now()),
            last_raised_at=data.get("last_raised_at", iso_now()),
            resolved=bool(data.get("resolved", False)),
            resolved_at=data.get("resolved_at"),
            times_raised=int(data.get("times_raised", 1)),
            resolution_notes=data.get("resolution_notes"),
        )


@dataclass
class LeadMemory:
    lead_id: str
    preferred_language: Optional[str] = None
    conversation_stage: str = "intro"
    recent_turns: List[TurnRecord] = field(default_factory=list)
    all_objections: Dict[str, ObjectionRecord] = field(default_factory=dict)
    objection_order: List[str] = field(default_factory=list)
    resolved_objections: List[str] = field(default_factory=list)
    unresolved_objections: List[str] = field(default_factory=list)
    score_history: List[float] = field(default_factory=list)
    classification_history: List[str] = field(default_factory=list)
    last_score: float = 0.0
    current_classification: str = "cold"
    conversation_summary: str = ""
    full_conversation_summary: str = ""
    last_contacted_at: Optional[str] = None
    last_session_id: Optional[str] = None
    call_count: int = 0
    lead_profile: Dict[str, Any] = field(default_factory=dict)
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lead_id": self.lead_id,
            "preferred_language": self.preferred_language,
            "conversation_stage": self.conversation_stage,
            "recent_turns": [turn.to_dict() for turn in self.recent_turns],
            "all_objections": {
                key: record.to_dict() for key, record in self.all_objections.items()
            },
            "objection_order": list(self.objection_order),
            "resolved_objections": list(self.resolved_objections),
            "unresolved_objections": list(self.unresolved_objections),
            "score_history": list(self.score_history),
            "classification_history": list(self.classification_history),
            "last_score": self.last_score,
            "current_classification": self.current_classification,
            "conversation_summary": self.conversation_summary,
            "full_conversation_summary": self.full_conversation_summary,
            "last_contacted_at": self.last_contacted_at,
            "last_session_id": self.last_session_id,
            "call_count": self.call_count,
            "lead_profile": self.lead_profile,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LeadMemory":
        all_objections_raw = data.get("all_objections", {}) or {}
        all_objections = {
            key: ObjectionRecord.from_dict(value)
            for key, value in all_objections_raw.items()
        }

        return cls(
            lead_id=data.get("lead_id", ""),
            preferred_language=data.get("preferred_language"),
            conversation_stage=data.get("conversation_stage", "intro"),
            recent_turns=[
                TurnRecord.from_dict(item) for item in data.get("recent_turns", []) or []
            ],
            all_objections=all_objections,
            objection_order=list(data.get("objection_order", []) or []),
            resolved_objections=list(data.get("resolved_objections", []) or []),
            unresolved_objections=list(data.get("unresolved_objections", []) or []),
            score_history=[float(x) for x in data.get("score_history", []) or []],
            classification_history=list(data.get("classification_history", []) or []),
            last_score=float(data.get("last_score", 0.0)),
            current_classification=data.get("current_classification", "cold"),
            conversation_summary=data.get("conversation_summary", "") or "",
            full_conversation_summary=data.get("full_conversation_summary", "") or "",
            last_contacted_at=data.get("last_contacted_at"),
            last_session_id=data.get("last_session_id"),
            call_count=int(data.get("call_count", 0)),
            lead_profile=dict(data.get("lead_profile", {}) or {}),
            extra=dict(data.get("extra", {}) or {}),
        )


class MemoryManager:
    """
    Memory layer for Sambhaash AI.

    Responsibilities:
    - preserve short-term call context
    - preserve long-term lead context
    - track preferred language
    - track objections and resolution status
    - track score progression and classification history
    - produce prompt-ready snapshots for orchestrator.py

    This file intentionally does not:
    - call the LLM
    - calculate final lead score
    - perform vector search
    - write directly to Supabase/SQLAlchemy

    Those remain in orchestrator/scoring/database layers.
    """

    def __init__(
        self,
        store: Optional[MemoryStoreProtocol] = None,
        recent_turn_limit: int = 12,
    ) -> None:
        self.store = store
        self.recent_turn_limit = max(1, recent_turn_limit)
        self._cache: Dict[str, LeadMemory] = {}

    def create_new_memory(
        self,
        lead_id: str,
        lead_profile: Optional[Dict[str, Any]] = None,
        preferred_language: Optional[str] = None,
    ) -> LeadMemory:
        memory = LeadMemory(
            lead_id=lead_id,
            preferred_language=preferred_language,
            lead_profile=dict(lead_profile or {}),
            last_contacted_at=iso_now(),
            call_count=1,
        )
        self._cache[lead_id] = memory
        return memory

    def get_or_create(
        self,
        lead_id: str,
        lead_profile: Optional[Dict[str, Any]] = None,
    ) -> LeadMemory:
        memory = self.load(lead_id)
        if memory is None:
            return self.create_new_memory(lead_id=lead_id, lead_profile=lead_profile)
        if lead_profile:
            memory.lead_profile.update(lead_profile)
        self._cache[lead_id] = memory
        return memory

    def load(self, lead_id: str) -> Optional[LeadMemory]:
        if lead_id in self._cache:
            return self._cache[lead_id]

        if self.store is None:
            return None

        raw = self.store.load_lead_memory(lead_id)
        if not raw:
            return None

        memory = LeadMemory.from_dict(raw)
        self._cache[lead_id] = memory
        return memory

    def save(self, memory: LeadMemory) -> None:
        memory.last_contacted_at = memory.last_contacted_at or iso_now()
        self._cache[memory.lead_id] = memory

        if self.store is not None:
            self.store.save_lead_memory(memory.lead_id, memory.to_dict())

    def reset_session_state(
        self,
        lead_id: str,
        keep_language: bool = True,
    ) -> LeadMemory:
        """
        Resets short-term call state but preserves long-term memory.
        """
        existing = self.load(lead_id)
        if existing is None:
            return self.create_new_memory(lead_id)

        preferred_language = existing.preferred_language if keep_language else None
        lead_profile = dict(existing.lead_profile)

        refreshed = LeadMemory(
            lead_id=lead_id,
            preferred_language=preferred_language,
            lead_profile=lead_profile,
            call_count=existing.call_count + 1,
            last_contacted_at=iso_now(),
            last_session_id=str(uuid4()),
            score_history=list(existing.score_history),
            classification_history=list(existing.classification_history),
            current_classification=existing.current_classification,
            last_score=existing.last_score,
            conversation_summary=existing.conversation_summary,
            full_conversation_summary=existing.full_conversation_summary,
            resolved_objections=list(existing.resolved_objections),
            unresolved_objections=list(existing.unresolved_objections),
            objection_order=list(existing.objection_order),
            all_objections=dict(existing.all_objections),
            extra=dict(existing.extra),
        )
        self._cache[lead_id] = refreshed
        return refreshed

    def set_preferred_language(self, memory: LeadMemory, language: Optional[str]) -> None:
        language = normalize_text(language)
        if language:
            memory.preferred_language = language

    def set_session_id(self, memory: LeadMemory, session_id: Optional[str] = None) -> None:
        memory.last_session_id = session_id or str(uuid4())

    def set_stage(self, memory: LeadMemory, stage: ConversationStage | str) -> None:
        if isinstance(stage, ConversationStage):
            memory.conversation_stage = stage.value
        else:
            memory.conversation_stage = normalize_key(stage) or memory.conversation_stage

    def set_last_score(self, memory: LeadMemory, score: float) -> None:
        memory.last_score = float(score)
        memory.score_history.append(float(score))

    def set_classification(self, memory: LeadMemory, classification: str) -> None:
        classification = normalize_key(classification) or "cold"
        memory.current_classification = classification
        memory.classification_history.append(classification)

    def update_lead_profile(self, memory: LeadMemory, updates: Dict[str, Any]) -> None:
        if not updates:
            return
        memory.lead_profile.update(updates)

    def append_turn(
        self,
        memory: LeadMemory,
        speaker: str,
        text: str,
        language: Optional[str] = None,
        stage: Optional[ConversationStage | str] = None,
        intent: Optional[LeadIntent | str] = None,
        objection_type: Optional[str] = None,
        score_after_turn: Optional[float] = None,
    ) -> TurnRecord:
        turn = TurnRecord(
            turn_id=str(uuid4()),
            speaker=normalize_key(speaker) or "user",
            text=normalize_text(text),
            language=normalize_text(language) or None,
            stage=self._stage_value(stage) if stage is not None else memory.conversation_stage,
            intent=self._intent_value(intent) if intent is not None else "unknown",
            objection_type=normalize_key(objection_type) or None,
            score_after_turn=float(score_after_turn) if score_after_turn is not None else memory.last_score,
        )
        memory.recent_turns.append(turn)
        memory.recent_turns = memory.recent_turns[-self.recent_turn_limit :]
        if turn.language and not memory.preferred_language:
            memory.preferred_language = turn.language
        return turn

    def add_user_turn(
        self,
        memory: LeadMemory,
        text: str,
        language: Optional[str] = None,
        stage: Optional[ConversationStage | str] = None,
        intent: Optional[LeadIntent | str] = None,
        objection_type: Optional[str] = None,
        score_after_turn: Optional[float] = None,
    ) -> TurnRecord:
        return self.append_turn(
            memory=memory,
            speaker="user",
            text=text,
            language=language,
            stage=stage,
            intent=intent,
            objection_type=objection_type,
            score_after_turn=score_after_turn,
        )

    def add_assistant_turn(
        self,
        memory: LeadMemory,
        text: str,
        language: Optional[str] = None,
        stage: Optional[ConversationStage | str] = None,
        intent: Optional[LeadIntent | str] = None,
        score_after_turn: Optional[float] = None,
    ) -> TurnRecord:
        return self.append_turn(
            memory=memory,
            speaker="assistant",
            text=text,
            language=language,
            stage=stage,
            intent=intent,
            objection_type=None,
            score_after_turn=score_after_turn,
        )

    def add_objection(
        self,
        memory: LeadMemory,
        objection_type: str,
        notes: Optional[str] = None,
    ) -> ObjectionRecord:
        key = normalize_key(objection_type)
        if not key:
            raise ValueError("objection_type cannot be empty")

        existing = memory.all_objections.get(key)
        if existing is None:
            record = ObjectionRecord(
                objection_type=key,
                resolution_notes=notes,
            )
            memory.all_objections[key] = record
            memory.objection_order.append(key)
            if key not in memory.unresolved_objections:
                memory.unresolved_objections.append(key)
            return record

        existing.times_raised += 1
        existing.last_raised_at = iso_now()
        if notes:
            existing.resolution_notes = notes
        if key not in memory.unresolved_objections and not existing.resolved:
            memory.unresolved_objections.append(key)
        return existing

    def resolve_objection(
        self,
        memory: LeadMemory,
        objection_type: str,
        notes: Optional[str] = None,
    ) -> Optional[ObjectionRecord]:
        key = normalize_key(objection_type)
        record = memory.all_objections.get(key)
        if record is None:
            return None

        record.resolved = True
        record.resolved_at = iso_now()
        if notes:
            record.resolution_notes = notes

        if key in memory.unresolved_objections:
            memory.unresolved_objections.remove(key)
        if key not in memory.resolved_objections:
            memory.resolved_objections.append(key)
        return record

    def mark_objection_unresolved(
        self,
        memory: LeadMemory,
        objection_type: str,
        notes: Optional[str] = None,
    ) -> Optional[ObjectionRecord]:
        key = normalize_key(objection_type)
        record = memory.all_objections.get(key)
        if record is None:
            return None

        record.resolved = False
        record.resolved_at = None
        if notes:
            record.resolution_notes = notes

        if key in memory.resolved_objections:
            memory.resolved_objections.remove(key)
        if key not in memory.unresolved_objections:
            memory.unresolved_objections.append(key)
        return record

    def update_summary(
        self,
        memory: LeadMemory,
        conversation_summary: Optional[str] = None,
        full_conversation_summary: Optional[str] = None,
    ) -> None:
        if conversation_summary is not None:
            memory.conversation_summary = normalize_text(conversation_summary)
        if full_conversation_summary is not None:
            memory.full_conversation_summary = normalize_text(full_conversation_summary)

    def append_summary_line(self, memory: LeadMemory, line: str) -> None:
        line = normalize_text(line)
        if not line:
            return
        if memory.full_conversation_summary:
            memory.full_conversation_summary += "\n"
        memory.full_conversation_summary += line

    def build_prompt_snapshot(self, memory: LeadMemory) -> Dict[str, Any]:
        """
        The orchestrator and prompt_builder should use this snapshot directly.
        """
        return {
            "lead_id": memory.lead_id,
            "preferred_language": memory.preferred_language,
            "conversation_stage": memory.conversation_stage,
            "current_classification": memory.current_classification,
            "last_score": memory.last_score,
            "score_history": list(memory.score_history),
            "classification_history": list(memory.classification_history),
            "resolved_objections": list(memory.resolved_objections),
            "unresolved_objections": list(memory.unresolved_objections),
            "objection_order": list(memory.objection_order),
            "conversation_summary": memory.conversation_summary,
            "full_conversation_summary": memory.full_conversation_summary,
            "lead_profile": dict(memory.lead_profile),
            "recent_turns": [turn.to_dict() for turn in memory.recent_turns],
            "last_contacted_at": memory.last_contacted_at,
            "last_session_id": memory.last_session_id,
            "call_count": memory.call_count,
            "extra": dict(memory.extra),
        }

    def build_context_text(self, memory: LeadMemory, max_turns: Optional[int] = None) -> str:
        """
        Compact text representation for prompt assembly.
        """
        recent_turns = memory.recent_turns[-(max_turns or self.recent_turn_limit) :]
        lines: List[str] = []

        if memory.conversation_summary:
            lines.append(f"Conversation summary: {memory.conversation_summary}")

        if memory.preferred_language:
            lines.append(f"Preferred language: {memory.preferred_language}")

        if memory.unresolved_objections:
            lines.append(
                "Unresolved objections: " + ", ".join(memory.unresolved_objections)
            )

        if memory.resolved_objections:
            lines.append("Resolved objections: " + ", ".join(memory.resolved_objections))

        if memory.lead_profile:
            profile_items = ", ".join(
                f"{k}={v}" for k, v in memory.lead_profile.items() if v not in (None, "", [], {}, ())
            )
            if profile_items:
                lines.append(f"Lead profile: {profile_items}")

        if recent_turns:
            lines.append("Recent turns:")
            for turn in recent_turns:
                lines.append(
                    f"- [{turn.speaker} | {turn.stage} | {turn.intent}] {turn.text}"
                )

        return "\n".join(lines).strip()

    def get_recent_turns(self, memory: LeadMemory, limit: Optional[int] = None) -> List[TurnRecord]:
        limit = limit or self.recent_turn_limit
        return memory.recent_turns[-limit:]

    def get_objection_status(self, memory: LeadMemory, objection_type: str) -> Dict[str, Any]:
        key = normalize_key(objection_type)
        record = memory.all_objections.get(key)
        if record is None:
            return {
                "exists": False,
                "objection_type": key,
                "resolved": False,
                "times_raised": 0,
            }
        return {
            "exists": True,
            "objection_type": key,
            "resolved": record.resolved,
            "times_raised": record.times_raised,
            "first_raised_at": record.first_raised_at,
            "last_raised_at": record.last_raised_at,
            "resolved_at": record.resolved_at,
            "resolution_notes": record.resolution_notes,
        }

    def has_open_objections(self, memory: LeadMemory) -> bool:
        return len(memory.unresolved_objections) > 0

    def get_open_objections(self, memory: LeadMemory) -> List[str]:
        return list(memory.unresolved_objections)

    def get_resolved_objections(self, memory: LeadMemory) -> List[str]:
        return list(memory.resolved_objections)

    def should_resume_from_memory(self, memory: LeadMemory) -> bool:
        """
        Useful for the orchestrator when a lead is contacted again.
        """
        return bool(
            memory.recent_turns
            or memory.conversation_summary
            or memory.preferred_language
            or memory.score_history
        )

    def snapshot_for_db(self, memory: LeadMemory) -> Dict[str, Any]:
        """
        DB-friendly payload. Keep this aligned with repository.py later.
        """
        return memory.to_dict()

    def merge_loaded_memory(
        self,
        lead_id: str,
        payload: Dict[str, Any],
    ) -> LeadMemory:
        memory = LeadMemory.from_dict(payload)
        memory.lead_id = lead_id or memory.lead_id
        self._cache[memory.lead_id] = memory
        return memory

    def clear_cache(self, lead_id: Optional[str] = None) -> None:
        if lead_id is None:
            self._cache.clear()
            return
        self._cache.pop(lead_id, None)

    def _stage_value(self, stage: Optional[ConversationStage | str]) -> str:
        if stage is None:
            return "intro"
        if isinstance(stage, ConversationStage):
            return stage.value
        return normalize_key(stage) or "intro"

    def _intent_value(self, intent: Optional[LeadIntent | str]) -> str:
        if intent is None:
            return "unknown"
        if isinstance(intent, LeadIntent):
            return intent.value
        return normalize_key(intent) or "unknown"

    def export_memory(self, lead_id: str) -> Optional[Dict[str, Any]]:
        memory = self.load(lead_id)
        if memory is None:
            return None
        return memory.to_dict()

    def import_memory(self, payload: Dict[str, Any]) -> LeadMemory:
        memory = LeadMemory.from_dict(payload)
        self._cache[memory.lead_id] = memory
        return memory

    def record_call_end(
        self,
        memory: LeadMemory,
        summary: Optional[str] = None,
        final_score: Optional[float] = None,
        final_classification: Optional[str] = None,
    ) -> None:
        if summary is not None:
            memory.conversation_summary = normalize_text(summary)
        if final_score is not None:
            self.set_last_score(memory, final_score)
        if final_classification is not None:
            self.set_classification(memory, final_classification)

    def ready_for_prompt(self, memory: LeadMemory) -> Dict[str, Any]:
        """
        Canonical shape intended for prompt_builder.py.
        """
        return {
            "lead_id": memory.lead_id,
            "preferred_language": memory.preferred_language or "english",
            "stage": memory.conversation_stage,
            "summary": memory.conversation_summary,
            "full_summary": memory.full_conversation_summary,
            "recent_turns": [turn.to_dict() for turn in self.get_recent_turns(memory)],
            "open_objections": self.get_open_objections(memory),
            "resolved_objections": self.get_resolved_objections(memory),
            "lead_profile": dict(memory.lead_profile),
            "score": memory.last_score,
            "classification": memory.current_classification,
            "call_count": memory.call_count,
            "last_session_id": memory.last_session_id,
        }