# Knowledge base

Documents the agent can draw on during a call.

## Ingest — `POST /admin/kb/upload`

Accepts `pdf`, `docx`, `json`, `txt` (multipart `file`, query `language`). The
file is stored in Supabase Storage, parsed (`services/document_parser.py`),
chunked (about 500 tokens), embedded, and written to `knowledge_base`.
Embedding happens before any row is written: if the embedding model is
unavailable the request fails with 503 and nothing is stored.

Other endpoints: `GET /admin/kb/documents`, `GET /admin/kb/documents/{id}`,
`DELETE /admin/kb/documents/{id}`, `GET /admin/kb/search?query=`,
`GET /admin/kb/stats`.

## Embeddings — `services/llm/embedder.py`

`sentence-transformers/all-MiniLM-L6-v2`, 384 dimensions, normalized, run
locally through fastembed (ONNX). No API key and no network call per query
(about 10–35 ms). The model downloads once into `EMBEDDING_CACHE_DIR`, loads at
API startup, and is baked into the Docker image. Failures raise
`EmbeddingError`; a zero vector is never returned.

## Retrieval — `services/llm/kb_context_injection.py`

Per caller turn: embed the utterance, cosine similarity against stored chunk
embeddings (`repository.vector_search_knowledge_base`, computed in Python),
keep results with score ≥ `min_score` (0.3), top 3. The formatted chunks go to
the `rag_node` prompt. If retrieval fails the call continues without context.
Each lookup is appended to `call_sessions.kb_usage_log` in the background.

`knowledge_base.embedding` is a JSON text column, so this is a linear scan; it
is fine for hundreds of chunks, not for hundreds of thousands.

## Analytics

All computed from `kb_usage_log`, nothing is invented.

| Endpoint | Returns |
|---|---|
| `GET /admin/kb/analytics/effectiveness?limit_days=` | calls, calls using the KB, lookups per call, mean relevance, most-used documents |
| `GET /admin/kb/analytics/call/{session_id}` | one call's lookups and documents |
| `GET /admin/kb/analytics/document-impact/{doc_id}` | retrievals, relevance, calls, converted leads, top queries |

With no usage the numbers are zero and the document list is empty.

## Quality notes

- Retrieval is only as good as the content. The shipped KB is a single short
  appendix (3 chunks); adding material helps more than tuning `min_score`.
- Matching is semantic for English; accuracy for other Indian languages depends
  on the multilingual coverage of MiniLM and is not measured.
