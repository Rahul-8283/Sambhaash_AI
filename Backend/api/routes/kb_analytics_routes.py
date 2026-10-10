"""
Phase 2A: KB Usage Analytics Routes
Tracks and reports KB context usage in calls
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from uuid import UUID
import logging

from services.database.supabase_client import get_db_client, SupabaseClient
from services.database.repository import Repository
from services.llm.kb_context_injection import KBContextInjectionService, parse_usage_log

logger = logging.getLogger(__name__)

from api.auth import get_current_user

router = APIRouter(prefix="/admin/kb/analytics", tags=["admin-kb-analytics"], dependencies=[Depends(get_current_user)])
class KBUsageEntry(BaseModel):
    """Single KB usage entry from a call turn"""
    timestamp: str
    query: str
    documents_used: List[str]
    relevance_scores: List[float]


class CallKBAnalytics(BaseModel):
    """KB usage analytics for a single call"""
    call_session_id: str
    total_queries: int
    total_documents_used: int
    unique_documents: int
    avg_relevance_score: float
    documents_list: List[str]
    usage_log: List[KBUsageEntry]


class KBEffectivenessMetrics(BaseModel):
    """Metrics about KB effectiveness across calls"""
    total_calls_analyzed: int
    calls_with_kb_usage: int
    avg_documents_per_call: float
    avg_relevance_score: float
    most_used_documents: List[Dict[str, Any]]
    kb_coverage_percentage: float


# ==================== ROUTES ====================


@router.get(
    "/call/{session_id}",
    response_model=CallKBAnalytics,
    summary="Get KB analytics for a specific call session"
)
async def get_call_kb_analytics(
    session_id: str,
    db: SupabaseClient = Depends(get_db_client),
) -> CallKBAnalytics:
    """
    Get detailed KB usage analytics for a call session.
    
    Shows:
    - Number of KB queries during the call
    - Which documents were used
    - Relevance scores for each document
    - Timeline of KB usage
    """
    try:
        kb_service = KBContextInjectionService(db_client=db)
        analytics = await kb_service.get_kb_analytics_for_call(UUID(session_id))
        
        if "error" in analytics:
            raise HTTPException(status_code=404, detail=analytics["error"])
        
        logger.info(f"[KB_ANALYTICS] Retrieved analytics for call {session_id}")
        
        # Format usage log
        usage_log = [
            KBUsageEntry(
                timestamp=entry.get("timestamp", ""),
                query=entry.get("query", ""),
                documents_used=entry.get("documents_used", []),
                relevance_scores=entry.get("relevance_scores", [])
            )
            for entry in analytics.get("usage_log", [])
        ]
        
        return CallKBAnalytics(
            call_session_id=session_id,
            total_queries=analytics.get("total_queries", 0),
            total_documents_used=analytics.get("total_documents_used", 0),
            unique_documents=analytics.get("unique_documents", 0),
            avg_relevance_score=analytics.get("avg_relevance_score", 0.0),
            documents_list=analytics.get("documents_list", []),
            usage_log=usage_log
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[KB_ANALYTICS] Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get analytics")


def _usage_entries(raw) -> List[Dict[str, Any]]:
    """Valid usage entries (dicts) from a session's kb_usage_log."""
    return [e for e in parse_usage_log(raw) if isinstance(e, dict)]


@router.get(
    "/effectiveness",
    response_model=KBEffectivenessMetrics,
    summary="Get KB effectiveness metrics across all calls"
)
async def get_kb_effectiveness(
    db: SupabaseClient = Depends(get_db_client),
    limit_days: int = Query(7, ge=1, le=90, description="Analyze last N days"),
) -> KBEffectivenessMetrics:
    """
    Aggregate KB usage over the last N days, computed from each call's kb_usage_log.

    - total_calls_analyzed: calls started in the window
    - calls_with_kb_usage: calls where at least one KB lookup returned context
    - avg_documents_per_call: average KB lookups per call
    - avg_relevance_score: mean similarity of every retrieved chunk (0 if none)
    - most_used_documents: documents by number of retrievals
    - kb_coverage_percentage: % of calls that used the KB

    With no usage the metrics are zero and the list is empty.
    """
    try:
        repo = Repository(db)

        rows = await repo.db.execute_query(
            """
            SELECT kb_usage_log
            FROM call_sessions
            WHERE created_at > NOW() - make_interval(days => $1)
            """,
            (limit_days,),
        )

        total_calls = len(rows)
        calls_with_kb = 0
        total_queries = 0
        all_scores: List[float] = []
        doc_counts: Dict[str, int] = {}
        doc_scores: Dict[str, List[float]] = {}

        for row in rows:
            entries = _usage_entries(row.get("kb_usage_log"))
            total_queries += len(entries)
            used_kb = False
            for entry in entries:
                docs = entry.get("documents_used") or []
                scores = entry.get("relevance_scores") or []
                for idx, doc_id in enumerate(docs):
                    used_kb = True
                    doc_counts[doc_id] = doc_counts.get(doc_id, 0) + 1
                    if idx < len(scores):
                        all_scores.append(float(scores[idx]))
                        doc_scores.setdefault(doc_id, []).append(float(scores[idx]))
            if used_kb:
                calls_with_kb += 1

        top = sorted(doc_counts.items(), key=lambda kv: kv[1], reverse=True)[:5]
        names: Dict[str, str] = {}
        if top:
            for doc in await repo.list_documents():
                names[str(doc.get("id"))] = doc.get("file_name") or "Unknown document"

        most_used_documents = [
            {
                "document_id": doc_id,
                "document_name": names.get(doc_id, "Deleted document"),
                "usage_count": count,
                "avg_relevance": round(sum(doc_scores[doc_id]) / len(doc_scores[doc_id]), 2)
                if doc_scores.get(doc_id) else 0.0,
            }
            for doc_id, count in top
        ]

        logger.info(f"[KB_ANALYTICS] Effectiveness: {calls_with_kb}/{total_calls} calls used KB")

        return KBEffectivenessMetrics(
            total_calls_analyzed=total_calls,
            calls_with_kb_usage=calls_with_kb,
            avg_documents_per_call=(total_queries / total_calls) if total_calls else 0.0,
            avg_relevance_score=(sum(all_scores) / len(all_scores)) if all_scores else 0.0,
            most_used_documents=most_used_documents,
            kb_coverage_percentage=(calls_with_kb / total_calls * 100) if total_calls else 0.0,
        )

    except Exception as e:
        logger.error(f"[KB_ANALYTICS] Effectiveness error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get effectiveness metrics")


@router.get(
    "/document-impact/{doc_id}",
    response_model=Dict[str, Any],
    summary="Get impact metrics for a specific KB document"
)
async def get_document_impact(
    doc_id: UUID,
    limit_days: int = Query(30, ge=1, le=365, description="Analyze last N days"),
    db: SupabaseClient = Depends(get_db_client),
) -> Dict[str, Any]:
    """
    How a document was used: retrievals, average relevance, calls that used it,
    how many of those leads were converted, and the queries that retrieved it.
    """
    try:
        repo = Repository(db)
        doc_key = str(doc_id)

        document = await repo.db.execute_fetchone(
            "SELECT id, file_name FROM documents WHERE id = $1", (doc_key,)
        )
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        rows = await repo.db.execute_query(
            """
            SELECT cs.kb_usage_log, l.status AS lead_status
            FROM call_sessions cs
            LEFT JOIN leads l ON l.id = cs.lead_id
            WHERE cs.created_at > NOW() - make_interval(days => $1)
            """,
            (limit_days,),
        )

        times_retrieved = 0
        scores: List[float] = []
        calls_using = 0
        converted = 0
        queries: Dict[str, int] = {}

        for row in rows:
            used = False
            for entry in _usage_entries(row.get("kb_usage_log")):
                docs = entry.get("documents_used") or []
                relevance = entry.get("relevance_scores") or []
                for idx, used_id in enumerate(docs):
                    if used_id != doc_key:
                        continue
                    used = True
                    times_retrieved += 1
                    if idx < len(relevance):
                        scores.append(float(relevance[idx]))
                    query = (entry.get("query") or "").strip()
                    if query:
                        queries[query] = queries.get(query, 0) + 1
            if used:
                calls_using += 1
                if str(row.get("lead_status") or "").upper() == "CONVERTED":
                    converted += 1

        top_queries = [
            {"query": q, "count": c}
            for q, c in sorted(queries.items(), key=lambda kv: kv[1], reverse=True)[:5]
        ]

        return {
            "document_id": doc_key,
            "document_name": document.get("file_name"),
            "days_analyzed": limit_days,
            "times_retrieved": times_retrieved,
            "avg_relevance_score": round(sum(scores) / len(scores), 3) if scores else 0.0,
            "calls_using_document": calls_using,
            "leads_converted_with_this_doc": converted,
            "conversion_rate": round(converted / calls_using, 3) if calls_using else 0.0,
            "top_queries": top_queries,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[KB_ANALYTICS] Document impact error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get document impact")
