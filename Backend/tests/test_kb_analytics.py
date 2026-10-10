import asyncio
import json

import api.routes.kb_analytics_routes as routes

DOC_A, DOC_B = "11111111-1111-1111-1111-111111111111", "22222222-2222-2222-2222-222222222222"


class FakeDB:
    def __init__(self, rows):
        self.rows = rows

    async def execute_query(self, query, params=()):
        return self.rows

    async def execute_fetchone(self, query, params=()):
        return {"id": DOC_A, "file_name": "Fees.pdf"}


def _patch_repo(monkeypatch):
    class FakeRepo:
        def __init__(self, db):
            self.db = db

        async def list_documents(self):
            return [{"id": DOC_A, "file_name": "Fees.pdf"}]

    monkeypatch.setattr(routes, "Repository", FakeRepo)


def test_effectiveness_aggregates_real_logs(monkeypatch):
    _patch_repo(monkeypatch)
    rows = [
        {"kb_usage_log": json.dumps([
            {"query": "price?", "documents_used": [DOC_A, DOC_B], "relevance_scores": [0.8, 0.6]},
            {"query": "fees", "documents_used": [DOC_A], "relevance_scores": [0.7]},
        ])},
        {"kb_usage_log": [{"query": "x", "documents_used": [DOC_A], "relevance_scores": [0.9]}]},
        {"kb_usage_log": "[]"},
        {"kb_usage_log": None},
    ]
    result = asyncio.run(routes.get_kb_effectiveness(db=FakeDB(rows), limit_days=7))
    assert result.total_calls_analyzed == 4
    assert result.calls_with_kb_usage == 2
    assert result.kb_coverage_percentage == 50.0
    assert result.avg_documents_per_call == 0.75
    assert result.avg_relevance_score == 0.75
    top = result.most_used_documents[0]
    assert (top["document_name"], top["usage_count"], top["avg_relevance"]) == ("Fees.pdf", 3, 0.8)
    assert result.most_used_documents[1]["document_name"] == "Deleted document"


def test_no_usage_means_zeros_not_invented_numbers(monkeypatch):
    _patch_repo(monkeypatch)
    result = asyncio.run(routes.get_kb_effectiveness(db=FakeDB([{"kb_usage_log": "[]"}]), limit_days=7))
    assert result.avg_relevance_score == 0.0
    assert result.most_used_documents == []
    assert result.calls_with_kb_usage == 0


def test_document_impact_counts_conversions(monkeypatch):
    _patch_repo(monkeypatch)
    rows = [
        {"kb_usage_log": json.dumps([{"query": "price?", "documents_used": [DOC_A], "relevance_scores": [0.8]}]), "lead_status": "CONVERTED"},
        {"kb_usage_log": json.dumps([{"query": "price?", "documents_used": [DOC_A], "relevance_scores": [0.6]}]), "lead_status": "CONTACTED"},
        {"kb_usage_log": json.dumps([{"query": "other", "documents_used": [DOC_B], "relevance_scores": [0.9]}]), "lead_status": "CONVERTED"},
    ]
    impact = asyncio.run(routes.get_document_impact(doc_id=DOC_A, limit_days=30, db=FakeDB(rows)))
    assert impact["times_retrieved"] == 2
    assert impact["calls_using_document"] == 2
    assert impact["leads_converted_with_this_doc"] == 1
    assert impact["conversion_rate"] == 0.5
    assert impact["top_queries"] == [{"query": "price?", "count": 2}]
