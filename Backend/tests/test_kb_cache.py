"""
The knowledge-base vectors are cached in-process: a live call turn was spending
1.27s re-reading three rows from Supabase and re-parsing their embeddings.
"""

import asyncio
import json

import pytest

from services.database import repository as repo_mod
from services.database.repository import Repository, invalidate_kb_cache


def _row(rid, vec, language="en", objection_type=None):
    return {
        "id": rid,
        "document_id": "doc-1",
        "text": f"chunk {rid}",
        "embedding": json.dumps(vec),
        "language": language,
        "objection_type": objection_type,
        "benefit_type": None,
        "source_section": None,
        "created_at": None,
        "file_name": "Partner.pdf",
        "document_type": "pdf",
    }


class CountingDB:
    def __init__(self, rows):
        self.rows = rows
        self.queries = 0

    async def execute_query(self, query, params=()):
        self.queries += 1
        return self.rows


@pytest.fixture(autouse=True)
def _clear_cache():
    invalidate_kb_cache()
    yield
    invalidate_kb_cache()


def _repo(rows):
    r = Repository.__new__(Repository)
    r.db = CountingDB(rows)
    return r


def test_second_search_is_served_from_cache():
    r = _repo([_row("a", [1.0, 0.0]), _row("b", [0.0, 1.0])])

    first = asyncio.run(r.vector_search_knowledge_base([1.0, 0.0], top_k=3))
    second = asyncio.run(r.vector_search_knowledge_base([1.0, 0.0], top_k=3))

    assert r.db.queries == 1, "the second turn must not hit the database"
    assert first[0]["id"] == "a" and first[0]["score"] == 1.0
    assert [x["id"] for x in first] == [x["id"] for x in second]


def test_scores_do_not_leak_between_searches():
    # the cached row must never be handed out directly, or one turn's score
    # would survive into the next
    r = _repo([_row("a", [1.0, 0.0])])
    asyncio.run(r.vector_search_knowledge_base([1.0, 0.0], top_k=3))
    again = asyncio.run(r.vector_search_knowledge_base([0.0, 1.0], top_k=3, min_score=0.0))
    assert again[0]["score"] == 0.0


def test_filters_are_applied_to_the_shared_candidate_set():
    r = _repo([
        _row("en1", [1.0, 0.0], language="en"),
        _row("hi1", [1.0, 0.0], language="hi"),
        _row("pr1", [1.0, 0.0], language="en", objection_type="price"),
    ])

    en = asyncio.run(r.vector_search_knowledge_base([1.0, 0.0], top_k=9, language="en"))
    hi = asyncio.run(r.vector_search_knowledge_base([1.0, 0.0], top_k=9, language="hi"))
    price = asyncio.run(r.vector_search_knowledge_base([1.0, 0.0], top_k=9, objection_type="price"))

    assert sorted(x["id"] for x in en) == ["en1", "pr1"]
    assert [x["id"] for x in hi] == ["hi1"]
    assert [x["id"] for x in price] == ["pr1"]
    assert r.db.queries == 1, "one candidate set serves every filter combination"


def test_min_score_still_drops_weak_matches():
    r = _repo([_row("a", [1.0, 0.0]), _row("b", [0.0, 1.0])])
    hits = asyncio.run(r.vector_search_knowledge_base([1.0, 0.0], top_k=3, min_score=0.3))
    assert [x["id"] for x in hits] == ["a"]


def test_invalidation_forces_a_reload():
    r = _repo([_row("a", [1.0, 0.0])])
    asyncio.run(r.vector_search_knowledge_base([1.0, 0.0]))
    invalidate_kb_cache()
    asyncio.run(r.vector_search_knowledge_base([1.0, 0.0]))
    assert r.db.queries == 2


def test_a_truncated_candidate_set_is_not_cached(monkeypatch):
    # filtering a partial set in Python would not match SQL-side filtering
    monkeypatch.setattr(repo_mod, "KB_SEARCH_CANDIDATE_LIMIT", 2)
    r = _repo([_row("a", [1.0, 0.0]), _row("b", [0.0, 1.0])])
    asyncio.run(r.vector_search_knowledge_base([1.0, 0.0]))
    asyncio.run(r.vector_search_knowledge_base([1.0, 0.0]))
    assert r.db.queries == 2


def test_unparseable_embedding_is_skipped():
    bad = _row("bad", [1.0, 0.0])
    bad["embedding"] = "not json"
    r = _repo([bad, _row("good", [1.0, 0.0])])
    hits = asyncio.run(r.vector_search_knowledge_base([1.0, 0.0], top_k=3))
    assert [x["id"] for x in hits] == ["good"]


def test_dimension_mismatch_is_skipped():
    r = _repo([_row("short", [1.0]), _row("ok", [1.0, 0.0])])
    hits = asyncio.run(r.vector_search_knowledge_base([1.0, 0.0], top_k=3))
    assert [x["id"] for x in hits] == ["ok"]
