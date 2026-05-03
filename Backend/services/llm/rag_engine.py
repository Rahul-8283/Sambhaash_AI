# services/llm/rag_engine.py

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Protocol, Sequence, Tuple, runtime_checkable
import math
import re
from uuid import uuid4

from .state_machine import ConversationStage


class KnowledgeSource(str, Enum):
    APPENDIX_A = "appendix_a"
    FAQ = "faq"
    SCRIPT = "script"
    POLICY = "policy"
    OTHER = "other"


@dataclass
class KnowledgeChunk:
    """
    Single retrievable unit stored in the vector DB.

    This is intentionally generic so it can map cleanly to:
    - Supabase + pgvector
    - any other vector store
    - a future repository abstraction
    """
    chunk_id: str
    document_id: str
    text: str
    source_type: str = KnowledgeSource.OTHER.value
    section_name: Optional[str] = None
    objection_tag: Optional[str] = None
    language_tag: Optional[str] = None
    stage_tag: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeChunk":
        return cls(
            chunk_id=str(data.get("chunk_id") or uuid4()),
            document_id=str(data.get("document_id") or ""),
            text=str(data.get("text") or data.get("chunk_text") or ""),
            source_type=str(data.get("source_type") or KnowledgeSource.OTHER.value),
            section_name=data.get("section_name"),
            objection_tag=data.get("objection_tag"),
            language_tag=data.get("language_tag"),
            stage_tag=data.get("stage_tag"),
            metadata=dict(data.get("metadata") or {}),
            embedding=data.get("embedding"),
        )


@dataclass
class RetrievalResult:
    chunk_id: str
    document_id: str
    text: str
    source_type: str
    section_name: Optional[str] = None
    objection_tag: Optional[str] = None
    language_tag: Optional[str] = None
    stage_tag: Optional[str] = None
    score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@runtime_checkable
class VectorStoreProtocol(Protocol):
    """
    Generic vector DB contract.

    Recommended implementation for the hackathon:
    - Supabase Postgres + pgvector

    You can implement this protocol in:
    - services/database/repository.py
    - a dedicated vector store adapter
    - a script ingestion helper
    """

    def upsert_chunks(self, chunks: Sequence[KnowledgeChunk]) -> None:
        ...

    def search(
        self,
        query_embedding: Sequence[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Sequence[Dict[str, Any]]:
        ...


@runtime_checkable
class EmbedderProtocol(Protocol):
    """
    Generic embedder contract.

    Plug in your embedding model here later.
    The RAG engine itself should stay independent from the provider.
    """

    def embed_text(self, text: str) -> List[float]:
        ...

    def embed_texts(self, texts: Sequence[str]) -> List[List[float]]:
        ...


class RAGEngine:
    """
    Retrieval-Augmented Generation engine for Sambhaash AI.

    Responsibilities:
    - ingest knowledge chunks into the vector DB
    - retrieve Appendix A / FAQ / script context
    - rank chunks with metadata-aware filtering
    - build compact grounded context for prompt_builder.py

    This module intentionally does not:
    - generate the final assistant reply
    - handle conversation state transitions
    - write to lead memory
    - perform lead scoring
    """

    def __init__(
        self,
        vector_store: Optional[VectorStoreProtocol] = None,
        embedder: Optional[EmbedderProtocol] = None,
        top_k: int = 5,
        model_name: str = "model name",
        api_key: str = "your api key",
    ) -> None:
        self.vector_store = vector_store
        self.embedder = embedder
        self.top_k = max(1, top_k)
        self.model_name = model_name
        self.api_key = api_key

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def ingest_chunks(self, chunks: Sequence[Dict[str, Any] | KnowledgeChunk]) -> List[KnowledgeChunk]:
        """
        Normalize and push chunks into the vector DB.

        The chunk format is intentionally flexible so your ingestion script
        can pass either raw dicts or KnowledgeChunk objects.
        """
        normalized: List[KnowledgeChunk] = []
        for chunk in chunks:
            if isinstance(chunk, KnowledgeChunk):
                normalized.append(chunk)
            else:
                normalized.append(KnowledgeChunk.from_dict(chunk))

        if self.vector_store is not None and normalized:
            self.vector_store.upsert_chunks(normalized)

        return normalized

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def retrieve(
        self,
        query_text: str,
        stage: Optional[ConversationStage | str] = None,
        objection_type: Optional[str] = None,
        language: Optional[str] = None,
        memory_snapshot: Optional[Dict[str, Any]] = None,
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve context relevant to:
        - current utterance
        - conversation stage
        - objection type
        - language style
        - memory snapshot

        Returns a list of grounded chunks sorted by relevance.
        """
        query_text = self._clean_text(query_text)
        if not query_text:
            return []

        stage_value = self._normalize_stage(stage)
        objection_value = self._normalize_objection(objection_type)
        language_value = self._normalize_language(language)

        query_bundle = self._build_query_bundle(
            query_text=query_text,
            stage=stage_value,
            objection_type=objection_value,
            language=language_value,
            memory_snapshot=memory_snapshot or {},
        )

        filters = self._build_filters(
            stage=stage_value,
            objection_type=objection_value,
            language=language_value,
            memory_snapshot=memory_snapshot or {},
        )

        if self.vector_store is not None and self.embedder is not None:
            query_embedding = self.embedder.embed_text(query_bundle)
            raw_results = list(
                self.vector_store.search(
                    query_embedding=query_embedding,
                    top_k=top_k or self.top_k,
                    filters=filters,
                )
            )
            parsed = [self._normalize_result(item) for item in raw_results]
            return self._rerank(parsed, query_text=query_text, stage=stage_value, objection_type=objection_value, language=language_value)

        # Fallback to lexical retrieval if vector store is not wired yet.
        # This keeps the project runnable during integration.
        return self._lexical_retrieve(
            query_bundle=query_bundle,
            query_text=query_text,
            stage=stage_value,
            objection_type=objection_value,
            language=language_value,
            memory_snapshot=memory_snapshot or {},
        )[: (top_k or self.top_k)]

    def retrieve_for_prompt(
        self,
        query_text: str,
        stage: Optional[ConversationStage | str] = None,
        objection_type: Optional[str] = None,
        language: Optional[str] = None,
        memory_snapshot: Optional[Dict[str, Any]] = None,
        top_k: Optional[int] = None,
    ) -> str:
        """
        Compact text block to inject into the system prompt.
        """
        chunks = self.retrieve(
            query_text=query_text,
            stage=stage,
            objection_type=objection_type,
            language=language,
            memory_snapshot=memory_snapshot,
            top_k=top_k,
        )

        if not chunks:
            return ""

        lines: List[str] = []
        for i, chunk in enumerate(chunks, start=1):
            prefix = f"[{i}]"
            section = chunk.get("section_name")
            if section:
                lines.append(f"{prefix} {section}: {chunk.get('text', '').strip()}")
            else:
                lines.append(f"{prefix} {chunk.get('text', '').strip()}")

        return "\n".join(lines).strip()

    # ------------------------------------------------------------------
    # Query construction
    # ------------------------------------------------------------------

    def _build_query_bundle(
        self,
        query_text: str,
        stage: str,
        objection_type: str,
        language: str,
        memory_snapshot: Dict[str, Any],
    ) -> str:
        """
        Build a single retrieval query that captures the conversation context.
        """
        parts = [query_text]

        if stage:
            parts.append(f"stage:{stage}")
        if objection_type and objection_type != "unknown":
            parts.append(f"objection:{objection_type}")
        if language:
            parts.append(f"language:{language}")

        summary = memory_snapshot.get("conversation_summary") or memory_snapshot.get("summary")
        if summary:
            parts.append(f"memory:{summary}")

        unresolved = memory_snapshot.get("unresolved_objections") or []
        if unresolved:
            parts.append("open_objections:" + ",".join(map(str, unresolved)))

        profile = memory_snapshot.get("lead_profile") or {}
        if profile:
            profile_bits = []
            for key in ("profession", "has_existing_clients", "network_size", "preferred_language"):
                if key in profile and profile[key] not in (None, "", [], {}, ()):
                    profile_bits.append(f"{key}={profile[key]}")
            if profile_bits:
                parts.append("profile:" + ";".join(profile_bits))

        return " | ".join(parts)

    def _build_filters(
        self,
        stage: str,
        objection_type: str,
        language: str,
        memory_snapshot: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Metadata filters for the vector store.

        Keep these simple and compatible with Supabase pgvector metadata filters.
        """
        filters: Dict[str, Any] = {}

        # Prefer Appendix A / FAQ / script content over generic sources.
        filters["source_type__in"] = [
            KnowledgeSource.APPENDIX_A.value,
            KnowledgeSource.FAQ.value,
            KnowledgeSource.SCRIPT.value,
            KnowledgeSource.POLICY.value,
        ]

        if stage:
            filters["stage_tag__in"] = [stage, "all"]
        if objection_type and objection_type != "unknown":
            filters["objection_tag__in"] = [objection_type, "all"]
        if language:
            filters["language_tag__in"] = [language, "all"]

        # Strongly prefer official script content when available.
        filters["section_name__not_null"] = True

        # You can extend these later in repository.py without changing the engine.
        if memory_snapshot.get("preferred_language"):
            filters["preferred_language"] = memory_snapshot["preferred_language"]

        return filters

    # ------------------------------------------------------------------
    # Reranking
    # ------------------------------------------------------------------

    def _rerank(
        self,
        results: List[RetrievalResult],
        query_text: str,
        stage: str,
        objection_type: str,
        language: str,
    ) -> List[Dict[str, Any]]:
        """
        Light reranking on top of vector similarity.

        This keeps output grounded and aligned with the call flow.
        """
        scored: List[Tuple[float, RetrievalResult]] = []
        for result in results:
            score = result.score

            # Boost relevance for matching stage / objection / language tags.
            if result.stage_tag and result.stage_tag.lower() in {stage, "all"}:
                score += 0.08
            if result.objection_tag and result.objection_tag.lower() in {objection_type, "all"}:
                score += 0.12
            if result.language_tag and result.language_tag.lower() in {language, "all"}:
                score += 0.05

            # Boost if the chunk clearly contains query terms.
            score += self._lexical_overlap_bonus(query_text, result.text)

            # Prefer official sources.
            if result.source_type in {
                KnowledgeSource.APPENDIX_A.value,
                KnowledgeSource.FAQ.value,
                KnowledgeSource.SCRIPT.value,
            }:
                score += 0.03

            scored.append((score, result))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [self._result_to_dict(result, score) for score, result in scored]

    def _lexical_retrieve(
        self,
        query_bundle: str,
        query_text: str,
        stage: str,
        objection_type: str,
        language: str,
        memory_snapshot: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Fallback retrieval mode if the vector DB is not wired yet.

        This is intentionally simple and deterministic so integration can proceed.
        """
        # Placeholder repository hook:
        # If your repository exposes a text search helper later, plug it in here.
        # For now, return an empty list rather than inventing data.
        return []

    # ------------------------------------------------------------------
    # Normalization helpers
    # ------------------------------------------------------------------

    def _normalize_result(self, item: Dict[str, Any]) -> RetrievalResult:
        metadata = dict(item.get("metadata") or {})
        return RetrievalResult(
            chunk_id=str(item.get("chunk_id") or item.get("id") or uuid4()),
            document_id=str(item.get("document_id") or ""),
            text=str(item.get("text") or item.get("chunk_text") or ""),
            source_type=str(item.get("source_type") or metadata.get("source_type") or KnowledgeSource.OTHER.value),
            section_name=item.get("section_name") or metadata.get("section_name"),
            objection_tag=item.get("objection_tag") or metadata.get("objection_tag"),
            language_tag=item.get("language_tag") or metadata.get("language_tag"),
            stage_tag=item.get("stage_tag") or metadata.get("stage_tag"),
            score=float(item.get("score") or item.get("similarity") or 0.0),
            metadata=metadata,
        )

    def _result_to_dict(self, result: RetrievalResult, score: float) -> Dict[str, Any]:
        payload = result.to_dict()
        payload["score"] = float(max(0.0, min(1.0, score)))
        return payload

    def _normalize_stage(self, stage: Optional[ConversationStage | str]) -> str:
        if stage is None:
            return "intro"
        if isinstance(stage, ConversationStage):
            return stage.value
        value = str(stage).strip().lower()
        valid = {s.value for s in ConversationStage}
        return value if value in valid else "intro"

    def _normalize_objection(self, objection_type: Optional[str]) -> str:
        value = str(objection_type or "").strip().lower()
        if not value:
            return "unknown"
        return value

    def _normalize_language(self, language: Optional[str]) -> str:
        value = str(language or "").strip().lower()
        if value in {"english", "hindi", "hinglish", "tamil", "telugu", "marathi", "gujarati", "bengali", "kannada"}:
            return value
        return "all"

    def _clean_text(self, text: Optional[str]) -> str:
        return re.sub(r"\s+", " ", (text or "").strip())

    # ------------------------------------------------------------------
    # Scoring helpers
    # ------------------------------------------------------------------

    def _lexical_overlap_bonus(self, query_text: str, chunk_text: str) -> float:
        """
        Small bonus based on shared meaningful terms.
        """
        query_tokens = self._tokenize(query_text)
        chunk_tokens = self._tokenize(chunk_text)

        if not query_tokens or not chunk_tokens:
            return 0.0

        query_set = set(query_tokens)
        chunk_set = set(chunk_tokens)

        overlap = len(query_set & chunk_set)
        if overlap == 0:
            return 0.0

        denom = max(1, len(query_set))
        return min(0.15, overlap / denom * 0.12)

    def _tokenize(self, text: str) -> List[str]:
        text = (text or "").lower()
        tokens = re.findall(r"[a-z0-9]+", text)
        stopwords = {
            "the", "and", "for", "are", "with", "that", "this", "what", "when", "from",
            "your", "you", "into", "our", "was", "were", "has", "have", "had", "will",
            "can", "could", "should", "would", "about", "how", "why", "which", "into",
            "their", "them", "they", "his", "her", "its", "but", "not", "who", "what",
            "is", "am", "an", "a", "to", "of", "in", "on", "at", "by", "it", "be",
        }
        return [t for t in tokens if t not in stopwords and len(t) > 1]

    def _confidence_from_embedding_score(self, score: float) -> float:
        """
        Normalize a vector score into 0..1 if needed.
        """
        if score is None:
            return 0.0
        return max(0.0, min(1.0, float(score)))

    # ------------------------------------------------------------------
    # Ingestion helpers for script usage
    # ------------------------------------------------------------------

    def chunk_text(
        self,
        text: str,
        document_id: str,
        source_type: str = KnowledgeSource.OTHER.value,
        section_name: Optional[str] = None,
        objection_tag: Optional[str] = None,
        language_tag: Optional[str] = None,
        stage_tag: Optional[str] = None,
        max_chars: int = 900,
        overlap_chars: int = 120,
    ) -> List[KnowledgeChunk]:
        """
        Simple chunker for Appendix A / FAQ ingestion.

        Keeps chunks meaningfully sized for retrieval without overfragmenting.
        """
        text = self._clean_text(text)
        if not text:
            return []

        max_chars = max(100, max_chars)
        overlap_chars = max(0, min(overlap_chars, max_chars // 2))

        chunks: List[KnowledgeChunk] = []
        start = 0
        length = len(text)

        while start < length:
            end = min(length, start + max_chars)

            # Try to end on a sentence boundary for cleaner chunks.
            if end < length:
                boundary = max(
                    text.rfind(". ", start, end),
                    text.rfind("? ", start, end),
                    text.rfind("! ", start, end),
                    text.rfind("\n", start, end),
                )
                if boundary > start + max_chars // 2:
                    end = boundary + 1

            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append(
                    KnowledgeChunk(
                        chunk_id=str(uuid4()),
                        document_id=document_id,
                        text=chunk_text,
                        source_type=source_type,
                        section_name=section_name,
                        objection_tag=objection_tag,
                        language_tag=language_tag,
                        stage_tag=stage_tag,
                    )
                )

            if end >= length:
                break

            start = max(0, end - overlap_chars)

        return chunks

    def build_knowledge_payload(
        self,
        text: str,
        document_id: str,
        source_type: str = KnowledgeSource.OTHER.value,
        section_name: Optional[str] = None,
        objection_tag: Optional[str] = None,
        language_tag: Optional[str] = None,
        stage_tag: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        max_chars: int = 900,
        overlap_chars: int = 120,
    ) -> List[Dict[str, Any]]:
        """
        Convenience helper for scripts/ingest_appendix.py.

        Returns plain dicts ready for repository/vector-store insertion.
        """
        chunks = self.chunk_text(
            text=text,
            document_id=document_id,
            source_type=source_type,
            section_name=section_name,
            objection_tag=objection_tag,
            language_tag=language_tag,
            stage_tag=stage_tag,
            max_chars=max_chars,
            overlap_chars=overlap_chars,
        )

        payload: List[Dict[str, Any]] = []
        for chunk in chunks:
            item = chunk.to_dict()
            item["metadata"] = dict(metadata or {})
            payload.append(item)
        return payload

    def build_context_block(
        self,
        query_text: str,
        stage: Optional[ConversationStage | str] = None,
        objection_type: Optional[str] = None,
        language: Optional[str] = None,
        memory_snapshot: Optional[Dict[str, Any]] = None,
        top_k: Optional[int] = None,
    ) -> str:
        """
        Returns a prompt-ready block of retrieved knowledge.

        This is the exact shape prompt_builder.py should consume.
        """
        results = self.retrieve(
            query_text=query_text,
            stage=stage,
            objection_type=objection_type,
            language=language,
            memory_snapshot=memory_snapshot,
            top_k=top_k,
        )
        if not results:
            return ""

        lines: List[str] = []
        for idx, item in enumerate(results, start=1):
            section = item.get("section_name") or "retrieved"
            text = str(item.get("text") or "").strip()
            lines.append(f"[KB {idx}] {section}: {text}")
        return "\n".join(lines).strip()