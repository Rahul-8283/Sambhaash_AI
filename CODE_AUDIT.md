# Sambhaash AI — Code Audit

Full line-by-line review of the codebase (~15.6k lines backend Python, ~5.3k lines frontend TypeScript). This documents everything found — architectural defects, dead code, functional bugs, and security issues — with file:line references. Nothing listed here has been fixed yet; this is a findings document only. **Fix log (uncommitted unless noted):** §10.5 COLD re-dial loop is fixed (committed on `fix/remediation`). Done: lead-intake phone normalization to E.164 and the initiator's REJECTED-only-on-permanent-failure fix (§5, `utils/phone.py`); §4 auth on admin/RM/KB/queue/summary/call/recordings routes, Twilio signature checks on all Twilio webhooks (`api/twilio_auth.py`), CORS/TrustedHost from config, generic 500 responses, DB password masked in `init_db.py`, and generic errors in `rm_routes` (committed as `539b203`, `496734d`); §12.2 leaderboard/RM stats `::float`→`::numeric` SQL fix; §5 ngrok JSON key mismatch; §5 call-recordings router mounted (auth-protected); §5 `GET /api/calls/status/{sid}` now fetches from Twilio; §5 summary now uses the lead's stored score; §3 language code normalization (`utils/language.py`) and a `conversion_en` WhatsApp template (new text, needs review); §8.1 classification casing aligned to backend `HOT/WARM/COLD`. Blocked on approval: §5 conversion notes need `scripts/migrations/001_rm_conversion_notes.sql` to be run on Supabase first. Open: everything else in §5–§11.

**Headline finding:** the product's three flagship features — the LangGraph conversational orchestrator, the pgvector RAG knowledge base, and the 10-language voice/WhatsApp support — are each either silently broken or fake in the current live code path. Details below.

---

## 1. Orchestration is broken (the issue you flagged)

### 1.1 Conversation memory is silently destroyed every turn — the core defect

`orchestration/checkpointer.py` implements `SupabaseCallSessionCheckpointer`, the LangGraph checkpointer that's supposed to persist conversation state to the `call_sessions.conversation_history` DB column between calls to `app.ainvoke()` (each Twilio recording webhook re-invokes the graph fresh — `api/routes/webhook_routes.py:380`).

Two different, incompatible things write to that same column:
- The checkpointer's `aput` (`checkpointer.py:99-122`) writes LangChain message dicts: `{"type": "human", "content": ...}`.
- `_save_conversation_turn` (`webhook_routes.py:66-103`), fired via `asyncio.create_task` right after every `app.ainvoke()` call, independently writes `{"user": ..., "ai": ..., "language": ..., "timestamp": ...}` turn objects.

Whichever write lands last wins, and timing favors the turn-dict format overwriting the checkpointer's. When `aget_tuple` (`checkpointer.py:52-63`) then reads that back, `msg.get("role") or msg.get("type")` and `msg.get("content")` are both `None` (neither key exists in the turn-dict schema) — every historical turn silently reconstructs as an **empty-content `HumanMessage`**. No exception is raised, so it looks like it works. Net effect: **the AI has no real memory of anything said earlier in the same phone call.**

Other checkpointer defects, same file:
- `alist` (`checkpointer.py:95-97`) is typed `AsyncIterator[CheckpointTuple]` but its body is a bare `yield` — yields `None` once instead of a real tuple. Currently unreachable (nothing calls `.alist()`), so latent rather than active.
- `aput_writes` (`checkpointer.py:131-133`) is a no-op (`pass`) — pending writes are silently discarded. Harmless only because the graph never uses interrupts today.
- No sync `get_tuple`/`put`/`list` implemented at all, only async variants — `app.invoke()` (sync) would fail if ever called.
- `channel_versions={}` / `versions_seen={}` (`checkpointer.py:78-79`) are always empty, so LangGraph's version-diffing has no real data — masked only because every webhook call re-runs the graph from the entry node in one pass.

### 1.2 Two complete, independent orchestration systems exist — only the dumb one runs

**Live path:** `api/routes/webhook_routes.py:359-380` → `orchestration/graph.py` (LangGraph, ~140 lines total across `graph.py`/`nodes.py`/`state.py`) → `orchestration/nodes.py`, which routes and scores using bare substring checks:

```python
# orchestration/nodes.py:17-22 — this is the entire routing logic
if "?" in last_message or "how" in last_message or "what" in last_message:
    return {"current_node": "rag_node"}
elif "expensive" in last_message or "not interested" in last_message or "no" in last_message:
    return {"current_node": "objection_handler_node"}
else:
    return {"current_node": "pitch_node"}
```

```python
# orchestration/nodes.py:75-80 — this is the entire outcome scoring logic
if "yes" in last_user_message or "interested" in last_user_message:
    outcome = "HOT"
elif "no" in last_user_message or "stop" in last_user_message:
    outcome = "COLD"
else:
    outcome = "WARM"
```

**Dead path:** `services/llm/orchestrator.py`'s `Orchestrator` class (971 lines) plus ~4,000 more lines of supporting modules (`state_machine.py`, `rag_engine.py`, `memory_manager.py`, `prompt_builder.py`, `intent_detector.py`, `objection_handler.py`) — a genuinely sophisticated LLM-based intent detection / conversation stage machine / RAG / memory / objection-handling system. It is fully built but **never executed**.

The wiring: `services/telephony/call_manager.py:28` constructs `Orchestrator`, and `CallManager.process_turn` (`call_manager.py:34-77`) is its only caller. But `CallManager.process_turn` is itself **never called anywhere** (confirmed by grep for `.process_turn(` — zero call sites outside its own definition). `webhook_routes.py:255` instantiates `CallManager()` but only ever calls `manager.generate_tts(...)` on it — never `.process_turn(...)`.

Result: **~5,000 lines of the "real" conversational brain sit completely unused while a ~140-line keyword-matching stub runs every live call.**

Even if `process_turn` were wired back in, it wouldn't work correctly out of the box:
- `orchestrator.py:118` — `MemoryManager()` is constructed with no `store` argument, so `MemoryManager.store` is always `None`. `memory_manager.py:204,244` then makes `load()`/`save()` no-ops whenever `store is None`. **Zero classes anywhere in the Backend implement the `MemoryStoreProtocol`** this expects — the persistent-memory layer was designed but never built. Memory would live only in an in-process dict and vanish on every restart or across multiple worker processes.
- `orchestrator.py:125` — `RAGEngine(model_name=..., api_key=...)` is constructed with no `vector_store`/`embedder`, so `retrieve()` always falls into `_lexical_retrieve()` (`rag_engine.py:406-423`), which is a stub that unconditionally returns `[]` ("return an empty list rather than inventing data," per its own comment). This orchestrator would never retrieve any knowledge-base content even if it ran.
- `orchestrator.py:114-115` — default constructor args are literal placeholder strings: `model_name: str = "model name"`, `api_key: str = "your api key"`.

### 1.3 The real scoring engine is also dead, and separately broken

`services/scoring/scoring_engine.py` (292 lines) plus `intent_score.py`, `sentiment_score.py`, `engagement_score.py` implement real, structured lead scoring. `worker/call_worker.py:279-298` handles `JobType.UPDATE_SCORE` by calling `ScoringEngine.recalculate_scores_for_session`, and `JobType.ASSIGN_RM` similarly — but **nothing in the codebase ever enqueues a job of either type** (grep-confirmed: `worker/queue_manager.py:39-40` defines the enum values, only `call_worker.py` consumes them, no producer exists anywhere).

In `webhook_routes.py`, `_score_and_assign_lead` (lines 106-200) accepts a `scoring_engine: ScoringEngine` parameter, constructs a real instance and passes it in at both call sites (lines 292, 534) — but **never references the parameter inside the function body**. Actual lead classification in production is computed from hardcoded default scores (`user_engagement = user_interest = user_sentiment = 70`) or the LangGraph's naive keyword-based `classification_override` — never via `ScoringEngine`.

Independently, even if this dead code were wired back in, it would be broken too: `scoring_engine.py:60-80` (`extract_user_messages`) expects conversation turns shaped `{"role": "user", "content": ...}`, but the only place history is ever written (`webhook_routes.py:86-91`) saves `{"user": ..., "ai": ..., "language": ..., "timestamp": ...}` — no `role`/`content` keys at all. It would silently score every call against an empty message list.

---

## 2. The RAG / knowledge-base retrieval is fake, not semantic search

`services/database/repository.py:736-803` (`vector_search_knowledge_base`) — the function meant to do pgvector similarity search never uses the query embedding for ranking. Its own comment admits it:

```python
# Note: pgvector is stored as JSON string, so we'll use LIMIT instead of vector ops
...
0.8 + (0 * length($1::text)) as score
...
ORDER BY kb.created_at DESC
LIMIT $2
```

Every result gets a **hardcoded fake similarity score of 0.8**, and "retrieval" is really just "N most recently uploaded KB rows," completely ignoring relevance to the query. This lines up with `services/database/models.py:219` — `KnowledgeBase.embedding = Column(String(None))`, a plain text column, not a real pgvector `Vector(n)` type. `scripts/init_db.py` does run `CREATE EXTENSION IF NOT EXISTS vector`, but the extension is enabled and never actually used.

Downstream, `services/llm/kb_context_injection.py` (the module actually used by the live webhook flow) calls `vector_search_knowledge_base` directly and:
- Constructs `self.rag_engine = RAGEngine()` (`kb_context_injection.py:56-57`) but never calls it — dead attribute, confirming `RAGEngine` is unused everywhere in the codebase, not only via the dead `Orchestrator`.
- Accepts a `min_score: float = 0.3` relevance-threshold parameter (passed explicitly from `webhook_routes.py:352`) but **never uses it** — no post-filtering by score happens, so low-relevance KB chunks can be injected into every live call's prompt regardless of the caller's requested threshold.
- Constructs a fresh `EmbedderService()` (`kb_context_injection.py:95`) on every single call turn instead of caching it — real per-turn overhead spinning up a new `InferenceClient`.

Separately, `services/llm/embedder.py:83-87,123-127` — both `embed_text` and `embed_texts` silently swallow **all** exceptions (network errors, auth failures, rate limits) and return zero-vectors, only logging an error. A broken/expired Hugging Face token or rate limiting would silently degrade KB retrieval to "no relevant results" indefinitely, with no visible error or alerting.

**Bottom line:** the README's "Dynamic RAG Knowledge Base... using pgvector" does not perform real semantic search anywhere in the current code.

---

## 3. The 10-language multilingual feature doesn't work as designed

`services/stt/language_detector.py:41-65` returns full words: `"english"`, `"hindi"`, `"hinglish"` — never 2-letter ISO codes. This value flows unchanged into two places that expect codes:

- `services/tts/sarvam_service.py:19-31,59` — `LANGUAGE_MAP` is keyed by 2-letter codes (`"en"`, `"hi"`, ...). `LANGUAGE_MAP.get("hindi", "en-IN")` never matches any key, so it silently falls back to `"en-IN"` **every single time**. **Every TTS voice reply is synthesized in English, regardless of what language the caller actually spoke.**
- `services/messaging/whatsapp_service.py:141-144` — `template_key = f"warm_follow_up_{language}"`, but templates are only keyed `_hi`/`_en`. A lead whose language is stored as `"hindi"`/`"english"`/`"hinglish"` never matches either key, so it always falls back to the English template — Hindi-speaking WARM leads get an English WhatsApp follow-up.
- `services/messaging/whatsapp_service.py:206-209` — `send_conversion_confirmation` has no `conversion_en` template at all (only `conversion_hi` exists) — English leads silently get a Hindi conversion message instead.
- `services/messaging/whatsapp_service.py:67-78` — a `hot_reminder_hi` template is defined but never sent by anything; `_process_send_whatsapp` in `call_worker.py` only handles `warm_follow_up`/`conversion`/`custom` message types. Dead template.

Separately, in the (already-dead) `services/llm/objection_handler.py:411-440` (`_localized_text`/`_translate_hint`), the functions that claim to produce Hindi/Hinglish objection responses both literally `return text` unchanged — the "localization" is a no-op even in the unused code path.

---

## 4. Security issues

| Issue | Location | Impact |
|---|---|---|
| Almost no route authentication | Only `lead_routes.py` applies `Depends(get_current_user)` (`lead_routes.py:135`). `admin_routes.py`, `rm_routes.py`, `call_recordings_routes.py`, `kb_analytics_routes.py`, `queue_routes.py`, `summary_routes.py`, `call_routes.py` have **zero auth** despite a working Supabase-JWT mechanism (`api/auth.py`) existing and being used elsewhere. | Anyone can upload/delete KB documents, reassign/convert leads, download customer call-recording audio, retry the dead-letter queue, etc. |
| Unauthenticated outbound call/message trigger | `api/routes/call_routes.py:22-34,37-52` (`POST /api/calls/outbound`, `POST /api/calls/whatsapp`) — no auth, no rate limit. | Anyone who finds the URL can make the system place a real phone call or send a WhatsApp message from the business number to any number they supply — toll-fraud/spam/cost-abuse vector. |
| No Twilio signature verification | Every webhook in `api/routes/webhook_routes.py` and `whatsapp_routes.py` — no `X-Twilio-Signature` check anywhere. | Anyone who discovers the webhook URL can POST arbitrary form values, triggering fake call turns, spoofed recordings, or WhatsApp sends to real leads. |
| CORS + credentials footgun | `main.py:86-92` — `allow_origins=["*"]` combined with `allow_credentials=True` (Starlette dynamically echoes back the request Origin in this combination). `TrustedHostMiddleware(allowed_hosts=["*"])` (`main.py:95-98`) neutralizes host-header protection too. No environment-based conditional — this "development" config (per its own inline comment) is what ships to production. | Any website can make credentialed cross-origin requests against the API. |
| Internal errors leaked to clients | `main.py:142-152` — the global exception handler returns `str(exc)` directly in the JSON response body. | Stack traces / internal service error text exposed to any caller. |
| Dead secret validation | `config.py:136-153` — `_validate_config` is meant to fail startup if `GROQ_API_KEY`/`HF_API_KEY`/`DATABASE_URL` are missing, but every one of them has a non-empty placeholder default (e.g. `"sk-test-default"`), so `if not getattr(config, field)` can never be true. The app "boots successfully" with fake credentials and fails confusingly downstream instead of erroring clearly at startup. | Misconfiguration is discovered late, as opaque runtime failures. |
| Plaintext DB credential in logs | `scripts/init_db.py:30` — `print(f"📡 Connecting to: {database_url}")` prints the full connection string, **including the password**, to stdout. | Credential leak in logs/CI output/terminal history. |
| Fabricated analytics presented as real | `api/routes/kb_analytics_routes.py:199-289` — `get_kb_effectiveness` invents `usage_count`/`avg_relevance` values for documents with no real usage data yet (comment: *"Give it beautiful, distinct usage counts and relevance scores for presentation"*), falls back to fully hardcoded fake documents when no real data exists, hardcodes `avg_relevance_score=0.75`, and `get_document_impact` is a **100% hardcoded stub** returning identical canned metrics for every document, real or not (comment: *"In production, would query call sessions..."*). | Dashboard shows fabricated numbers indistinguishable from real analytics. |
| Fragile SQL string interpolation | `kb_analytics_routes.py:133-141,153-165` — `INTERVAL '{limit_days} days'` built via f-string; not exploitable today only because FastAPI/pydantic coerces `limit_days` to `int` first via `Query(..., ge=1, le=90)`. | Latent SQL injection surface if the validation is ever loosened. |

---

## 5. Backend correctness bugs

- **`worker/queue_manager.py:20,59-63` and throughout** — uses the synchronous `redis` client (not `redis.asyncio`), but every method is declared `async def` and calls `.set/.get/.zadd/.zrange/.keys(...)` with no `await`. Every "async" queue operation is actually a blocking network call that stalls the event loop.
- **`worker/queue_manager.py:141,152,170`** (`dequeue_job`) — reads the next job via `zrange` then deletes it via `zrem` as two separate, non-atomic Redis calls. Since `call_worker.py` runs 3 concurrent poll loops per job type, two workers can read the same job before either removes it, causing duplicate processing (e.g. a WhatsApp message sent twice). No atomic pop/Lua script guards this.
- **`worker/queue_manager.py:240`** — comment claims "Exponential backoff: 1s, 4s, 16s" but `2 ** (retries - 1)` actually yields 1s, 2s, 4s.
- **`worker/queue_manager.py:308-310,326-327`** — uses Redis `KEYS` (blocking O(N) full-keyspace scan) for stats/DLQ listing instead of `SCAN`, compounding the blocking-event-loop issue under load.
- **`worker/call_initiator.py:18`** (`from api.routes.webhook_routes import call_sessions`) — the worker and the FastAPI app run as **separate OS processes** in every real deployment (confirmed via `Dockerfile:32`'s `CMD ["sh","-c","python run_worker.py & uvicorn main:app ..."]` and `docker-compose.yml`'s separate `api`/`worker` containers), so this import gives the worker its own disconnected copy of the dict. Pre-registration writes at `call_initiator.py:173-179,196-199` are invisible to the process handling the real Twilio webhook — silently non-functional, masked only because `session_id`/`lead_id` are redundantly also passed via the webhook URL query string.
- **`worker/call_initiator.py:221`** — exception handler references `phone`, which is only assigned earlier in the same `try` block; an exception before that point (e.g. UUID parsing) raises `UnboundLocalError` here, masking the real error.
- **`worker/call_initiator.py:213-217,235-243`** — any failure at all (including a transient network/DB blip) permanently marks the lead `REJECTED`, with no retry/backoff and no distinction from a genuinely invalid phone number.
- **`services/stt/whisper_service.py:51-63`** (`transcribe_recording_url`) — fully synchronous (blocking `requests.get` + blocking OpenAI SDK call), invoked directly (not via `asyncio.to_thread`) from the async `recording_webhook` handler (`webhook_routes.py:328`). Blocks the entire event loop for the duration of download + transcription, freezing all other concurrent calls on the same worker process.
- **`services/messaging/whatsapp_service.py:307-311`** (`_send_via_twilio`) — calls the synchronous Twilio SDK's `messages.create()` without `asyncio.to_thread`, same event-loop-blocking issue on every WhatsApp/summary send.
- **`services/ngrok_setup.py:109`** writes `{"ngrok_url": tunnel_url, ...}` to `ngrok_url.json`, but **`services/telephony/twilio_client.py:73` reads it back with `data.get("url", base)`** — wrong key name, so the auto-detected ngrok URL is never actually picked up; the client silently keeps using the stale configured base URL.
- **`services/telephony/twilio_client.py:103-109`** (`download_recording`) is dead code — never called; `call_recording_service.py` and `whisper_service.py` each independently reimplement the same download logic instead of reusing it.
- **`services/messaging/whatsapp_service.py:300-301`** — `if not phone.startswith("+"): phone = "+91" + phone` hardcodes an India-only country code with no digit/format validation; malformed CSV-uploaded numbers (dashes, spaces, leading `0`) get sent straight to Twilio.
- **`services/call_recording_service.py:41`** — `WhisperService()` is instantiated eagerly in `CallRecordingService.__init__`, which raises `ValueError` if `GROQ_API_KEY` is missing/placeholder — merely constructing `CallRecordingService()` crashes the whole feature if the key isn't set, instead of failing lazily only when actually used.
- **`services/call_recording_service.py:210-261`** (`_extract_topics`, `_analyze_sentiment`) reimplement crude keyword-list sentiment/topic extraction, duplicating (and far cruder than) the dedicated `services/scoring/sentiment_score.py` that exists elsewhere but isn't reused here.
- **`services/tts/audio_formatter.py:14-36`** — `format_for_twilio` doesn't actually reformat/transcode non-conforming audio despite its name; it only logs a warning if channels/sample-width/rate don't match Twilio's requirements, then returns the original bytes unchanged.
- **`api/routes/public_routes.py:50`** — `return lead` returns the raw DB record (snake_case: `created_at`, `updated_at`, ...) directly against `response_model=LeadResponse`, which expects camelCase (`createdAt`, `currentScore`, `rmAssignment`, ...) normally produced via `_format_lead_response()` in `lead_routes.py`. The landing-page lead-capture endpoint likely 500s or silently drops fields on every call.
- **`api/routes/call_routes.py:55-61`** (`get_call_status`) is a fully hardcoded stub — never calls Twilio's API, always returns the same fake `"status": "tracked_by_twilio"` regardless of the `call_sid` given, including nonexistent ones.
- **`api/routes/call_recordings_routes.py`** (391 lines, fully implemented: list/search/download/transcription/statistics/audio-stream) is **never imported or mounted in `main.py`** — the entire "Call Recordings" feature 404s in production, despite the frontend calling it (`apiService.ts:378` → `GET /admin/recordings`). `api/routes/health.py`'s router is similarly never mounted (main.py defines its own separate inline `/health` instead).
- **`api/routes/call_recordings_routes.py:328-358`** (`get_recording_stats`) hardcodes `avg_duration = 0.0` and `total_storage = 0` instead of reading the real values already computed in the `stats` dict — always reports zero regardless of actual data (moot until the router is mounted).
- **`api/routes/rm_routes.py:205-252`** (`mark_lead_converted`) accepts `request.notes` (conversion notes) but never persists or reads them anywhere — silently discarded.
- **`services/llm/summary_generator.py`** cross-file: `worker/call_worker.py:232-235` passes `memory_snapshot={"current_classification": session.get("classification")}` — missing `last_score`/`final_score`/etc. — so the generated call summary's "FINAL SCORE" section always reads the `.get("last_score", 0.0)` default, i.e. **every summary reports a score of 0.0** regardless of the lead's actual score.
- **`services/llm/response_validator.py:51`** (`validate_or_fix`) is dead code (zero callers anywhere); only `validate_summary` is used. Turn-level LLM output validation instead relies on ad hoc inline normalization inside the (also dead) `Orchestrator`, duplicating logic that could drift out of sync.
- **`services/llm/language_policy.py`** (`LanguagePolicy` class) is fully dead code — zero instantiations anywhere outside its own definition/re-export.
- **`services/llm/intent_detector.py:24`** (`ObjectionType.NONE = "null"`) vs **`services/llm/objection_handler.py:20`** (`ObjectionType.UNKNOWN = "unknown"`) — two independently defined `ObjectionType` enums with different member names/values for the same "no objection" case, no shared source of truth.
- **`services/llm/objection_handler.py:266`** — `resolved = False` is hardcoded unconditionally in `_build_plan`; the deterministic fallback objection-handling path can never mark an objection resolved, unlike the primary LLM JSON path.
- **`services/llm/llm_client.py:174`** — hardcodes a spoofed browser `User-Agent` string on every LLM API request, looking like an attempt to dodge provider bot-filtering — worth checking against the provider's ToS.
- **`services/llm/llm_client.py:150`** — uses blocking `urllib.request.urlopen` (no async/httpx) for all HTTP calls; tolerable only because the whole (dead) orchestrator chain is wrapped in a single `asyncio.to_thread`, but would hurt the README's "sub-second latency" goal if ever revived.
- **`test_initiator.py:19`** calls `repo.list_leads_by_status("NEW", ...)` with a hardcoded literal `"NEW"`, while production code always uses `LeadStatus.NEW.value` — worth double-checking the enum's actual value matches, or this debug script always reports zero leads.

---

## 6. Empty / incomplete files

- **`Backend/utils/audio_utils.py`, `utils/logger.py`, `utils/text_utils.py`, `utils/__init__.py`** — all four are completely empty (0 bytes). An entire `utils` package exists in name only.
- **`Backend/scripts/ingest_appendix.py`** — completely empty (0 bytes). Given `Appendix/appendix.pdf` exists and the README advertises a "Dynamic RAG Knowledge Base," this looks like the intended KB-ingestion entrypoint that was never implemented.
- **`Backend/start_all.py`** — not invoked by the Dockerfile `CMD`, docker-compose, or render.yaml (grep-confirmed) — leftover/dead alternate bootstrap code.

---

## 7. Infra / dependency inconsistencies

- **`docker-compose.yml:28,65`** reference Docker multi-stage build targets `production` and `worker` that **do not exist** in `Backend/Dockerfile` (a single unnamed stage). `docker-compose up` as checked in would fail immediately with a missing-build-target error.
- The Dockerfile (`Dockerfile:32`) and docker-compose both run the API and the background worker as **separate processes/containers**, which is the root cause of the `call_sessions` dict-sharing bug in section 5.
- **`requirements.txt`** — `langgraph>=0.1.0`, `langchain>=0.2.0`, `langchain-core>=0.2.0`, `langchain-community>=0.2.0`, `langchain-groq>=0.1.0` have no upper bound on fast-moving pre-1.0 libraries, while `orchestration/checkpointer.py` hand-implements exact internal shapes of one of them (`Checkpoint` fields, `BaseCheckpointSaver` methods) — an unpinned install can silently resolve to an incompatible version.
- **`requirements.txt`** — `redis>=5.0.1` only pulls the sync client, consistent with the blocking-event-loop bug above; no async Redis client is used despite the async-looking `QueueManager` API.
- **`requirements.txt`** — `google-generativeai`, `psycopg2-binary`, `librosa` are never imported anywhere in `Backend/` (grep-confirmed) — dead dependencies adding install weight for zero use.
- **`Backend/test_output_twilio.wav`** is committed to the repo (produced by `scripts/test_call.py:32-34` writing to cwd); `.gitignore` has no `*.wav` rule.
- **`Backend/check_leads.py`, `Backend/test_initiator.py`** are ad hoc debug scripts left at the `Backend/` root instead of in `scripts/`, inconsistent with the project's own layout convention.

---

## 8. Frontend bugs

### 8.1 Classification casing mismatch — likely the single highest-impact frontend bug

The backend stores lead classification as uppercase (`"HOT"`/`"WARM"`/`"COLD"`, confirmed at `orchestration/nodes.py` and `CallSummaries.tsx:54-56` which checks uppercase directly). But:

- **`src/types/index.ts:10`** — `ScoreClassification = "Hot" | "Warm" | "Cold" | "Unscored"` (Title-case) is the root cause.
- **`src/components/Badge.tsx:31-32`** — `isScoreClassification` only matches Title-case, so a real lead's score Badge never matches and silently falls back to default gray styling with no icon — color-coding never renders for real data.
- **`src/pages/RMPage.tsx:41-43`** — `fetchHotLeads` queries `classification: ["Hot"]`; against real data stored as `"HOT"`, this almost certainly always returns an empty list. **The entire "RM Control Desk" page silently shows "No HOT Leads Found" even when hot leads exist.**
- **`src/pages/LeadsPage.tsx:239-244`** — the Score filter dropdown sends `"Hot"/"Warm"/"Cold"`; if the backend does exact-string filtering, this filter always returns zero rows.
- **`src/pages/LeadDetailPage.tsx:212-229`** — same Title-case comparison bug for badge coloring on the lead detail page.

### 8.2 Other real bugs

- **`src/pages/LeadDetailPage.tsx:236`** — reads `session.conversationHistory[...].text`, but the backend's saved turn shape is `{user, ai, language, timestamp}` (`_save_conversation_turn` in webhook_routes.py) — there is no `.text` field, so this always renders "No speech recorded." even with full history present.
- **`src/pages/LeadDetailPage.tsx:293-295`** — "Save Notes" button has no `onClick`; the textarea above it is uncontrolled (no `value`/`onChange`). The entire "Internal Notes" feature does nothing.
- **`src/pages/LeadDetailPage.tsx:53`** — `lead.scoreHistory?.[0] || lead.currentScore` assumes index 0 is the latest score; if the backend returns history oldest-first, this silently shows the oldest score as "latest."
- **`src/pages/AnalyticsPage.tsx:56-72,82,102`** — no null-guards on metric fields; a fresh deployment with no analytics data yet throws (`.toFixed`/`.map` on `undefined`) and crashes the whole page — there's no error boundary anywhere in the app.
- **`src/pages/LeadsPage.tsx:140`** (`handleBulkDelete`) — uses `Promise.all`; if any single delete fails, the whole call rejects before the list refresh runs, so successfully-deleted leads keep showing as if nothing happened while the error toast implies total failure.
- **`src/components/DataTable.tsx:39,50-72`** — `selectedRows` is never reset/reconciled when the `data` prop changes (e.g. page or filter change), so stale selected ids can desync the "select all" checkbox from what's actually on screen.
- **`src/pages/QueueDashboard.tsx:55-60`** (`handleRetryAll`) — always shows an "All jobs queued for retry" success toast even if every individual retry failed.
- **`src/components/Layout/TopNav.tsx:14,105-114`** — the notification bell has no `onClick`, and its "3" badge count is a hardcoded `useState(3)` whose setter is never called — a permanently fake notification indicator.
- **`src/pages/ProfileSettingsPage.tsx:56-82`** — the editable "Role" field is never sent to the backend; it's persisted only to `localStorage`, giving a false impression of a saved server-side setting.
- **`src/pages/AppendixPage.tsx:89-91`** — "Clear All" button is just `alert("Please delete documents individually")` — implies bulk delete but does nothing.

- **`src/types/index.ts:9`** — `LeadStatus = "Not Called" | "Calling" | "Connected" | "No Answer" | "Failed" | "Completed"`, but the backend's lead statuses are `NEW | CONTACTED | INTERESTED | CONVERTED | REJECTED | FOLLOW_UP` (`models.py:28-35`). The TypeScript type does not describe real data, so `RMPage.tsx:79,254` (`lead.status === "Completed"`) can never match a real lead and the "converted" count/badge only works through `rmAssignment.converted`. Same root cause as the classification casing bug in §8.1; the two should be fixed together by aligning frontend types to the backend enums.

### 8.3 Dead / orphaned frontend code

- **`src/pages/CallsPage.tsx`** (120 lines, fully implemented) — not registered in any route in `App.tsx`; the only link to it (`Footer.tsx:32`) points at a route that doesn't exist and redirects to `/dashboard/leads` via the catch-all. A fully built call-recordings page is unreachable (consistent with its backend route also never being mounted — section 5).
- **`src/pages/UsersPage.tsx`, `src/pages/CampaignsPage.tsx`** — 5-line placeholder stubs, not routed, not linked anywhere.
- **`src/components/Layout/Sidebar.tsx`** — an entire older sidebar component superseded by `ModernSidebar.tsx`, confirmed unused via grep.
- **`src/utils/appendixStorage.ts`** (84 lines) — a full localStorage-based file-storage system, entirely unused (`AppendixPage.tsx` uses real server-backed API calls instead). Its own `MAX_FILE_SIZE = 50MB` constant would also exceed typical browser localStorage quotas if it were ever wired up.
- **`src/components/Layout/Footer.tsx:47-58`** — four "AI Config Workspace" buttons (Prompt Guidelines, Language Routing, Retry Policies, Webhooks & API Keys) have no `onClick` at all — pure decoration implying features that don't exist.
- **`src/pages/CallsPage.tsx:9`** — `const [page] = useState(1)` has no setter, so despite tracking a `total` count, there's no way to ever view recordings past the first 20 (moot while the page is unreachable).

### 8.4 ESLint findings (already known, not re-detailed here)

`npm run lint` reports 44 errors / 1 warning: ~25 `@typescript-eslint/no-explicit-any`, several unused `catch` vars with empty blocks, one `prefer-const`, and several `react-hooks` purity/set-state-in-effect warnings from a very new `eslint-plugin-react-hooks` version flagging the common `useEffect(() => { fetchX() }, [])` pattern (functionally harmless). `npx tsc -b` itself passes with zero type errors.

---

## 9. Summary of what actually runs vs. what was built

| Subsystem | What's built | What actually runs in production |
|---|---|---|
| Conversation orchestration | `services/llm/orchestrator.py` + 6 modules (~5,000 lines): real intent detection, conversation-stage state machine, RAG, memory, objection handling | `orchestration/nodes.py`: 3 substring checks for routing, 4 substring checks for outcome scoring — and even this loses conversation memory every turn (§1.1) |
| Lead scoring | `services/scoring/` — structured intent/sentiment/engagement scoring engine | Hardcoded `70/70/70` defaults in `webhook_routes.py`, or a keyword-derived override from the LangGraph stub |
| Knowledge-base retrieval | pgvector extension enabled, embedding pipeline (`embedder.py`) | Plain "most recent N rows," hardcoded `0.8` fake similarity score, embedding never used for ranking |
| Multilingual voice/WhatsApp | Sarvam BulBul V3 TTS + language-keyed WhatsApp templates | Language-code mismatch means TTS always falls back to English; WhatsApp templates mostly fall back to English or the wrong language |
| Call recordings dashboard | Fully implemented API (391 lines) + frontend page (120 lines) | Backend router never mounted, frontend page never routed — completely unreachable end-to-end |
| HOT → RM allocation | `assign_lead_to_rm`, RM queue/stats/convert endpoints, RM Control Desk page | Every HOT lead is written to one fixed name (`DEFAULT_RM_NAME`, default `"Auto"`); no roster, no notification, no live handoff (§10.3) |
| WARM → WhatsApp follow-up | Template service, worker job, LLM reply webhook | Depends on a Twilio sandbox setup that the code neither documents nor validates; fails outright unless the lead has opted in (§10.4) |
| COLD handling | Score row saved with `COLD` | Score is saved, but the lead is reset to `NEW` and re-dialed every 30 s cycle (§10.5) |

This table is the honest answer to "is the orchestration properly implemented": most of the sophisticated code exists, but it's disconnected from the live path, and the simple code that *is* live has its own memory-loss bug on top.

---

## 10. Lead-outcome pipeline review (HOT / WARM / COLD, multilanguage, CRM)

Follow-up review of six specific concerns raised after the first audit. Each was checked against the code; verdicts are noted per item. Items already covered earlier are cross-referenced instead of repeated.

### 10.1 Multilanguage — confirmed broken beyond what §3 already lists

§3 already covers the language-name/ISO-code mismatch that forces every TTS reply to English. Additional findings from this pass:

- **Only three languages are ever detected.** `services/stt/language_detector.py:59-60` returns `"hinglish"` for *any* `langdetect` result that isn't `hi` or `en`. A caller speaking Tamil, Telugu, Bengali, Marathi etc. in native script is labelled Hinglish, so the "10 languages" claim has no detection path behind it, independent of the TTS map bug.
- **The LLM is never told which language to reply in.** `lead_language` exists in `AgentState` (`orchestration/state.py:30`) and is passed in at `webhook_routes.py:372`, but no node in `orchestration/nodes.py` reads it. All system prompts are English-only; the reply language depends on the model happening to mirror the caller.
- **Whisper language hinting is effectively unused.** `whisper_service.py:40-45` can only hint `en`/`hi`, and the live call at `webhook_routes.py:329` passes no `language` at all, so STT is pure auto-detect for every language.
- **The lead's stored language is never updated from what was actually spoken.** No `update_lead(language=...)` call exists on the live path, so the WARM WhatsApp follow-up uses the CSV/default `"hi"` rather than the language of the call.
- **Hardcoded product copy.** `api/routes/whatsapp_routes.py:69-74` hardcodes a "Rupeezy" persona and a loan offer ("Instant ₹5,000+ loan, 0% processing fee"), while `prompt_builder.py` pitches the "Rupeezy Partner Program" — the two channels describe different products.

### 10.2 HOT/WARM/COLD scoring — partially working, confirmed

The "partial / some mock" recollection is accurate. Classification runs end to end and a `lead_scores` row is written every time, but the inputs are mostly placeholders:

- `_score_and_assign_lead` (`webhook_routes.py:106-200`) defaults `engagement = interest = sentiment = 70`, giving a composite of 0.70 → **WARM** whenever no override is supplied. At max turns the override is `"UNKNOWN"` (not in the allowed list), so it falls through to this default. Every stored score value is therefore `0.70` unless the keyword override fires (see also §1.3 — `ScoringEngine` is passed in but never used).
- The override comes from `scoring_node` (`orchestration/nodes.py:75-80`), which uses raw substring tests. `"no"` matches *know, now, note, nothing, another*; `"yes"` matches *yesterday*; `"how"` in the router matches *show*. A caller saying "I don't know" is scored **COLD** and the call is ended (`webhook_routes.py:388`, `is_ending = outcome in ["HOT","COLD"]`).
- Only the *last* user message is scored (`messages[-2]`), never the whole call, contradicting the README's "evaluates the entire transcript".
- **Hangup fallback always scores WARM.** `status_webhook` (`webhook_routes.py:488-545`, override at line 541) forces `classification_override="WARM"` for any completed call still in `CONTACTED`, regardless of what was said — a caller who hangs up angrily becomes a WARM lead and receives a WhatsApp follow-up.
- Real scoring exists in `services/scoring/` but is disconnected (§1.3).

### 10.3 HOT → CRM/RM allocation — placeholder, not a real allocation

- `webhook_routes.py:170-171` assigns **every** HOT lead to `get_config().default_rm_name` (`config.py:78`, default `"Auto"`). There is no RM table, roster, workload balancing or round-robin; `rm_assignments.rm_name` is just a free-text string.
- Nothing notifies the RM. There is no email/WhatsApp/push, and no live transfer (`<Dial>`) anywhere in the backend — the README's "instantly trigger a live handoff to a Relationship Manager" is not implemented. The call simply ends with the AI's closing line.
- The frontend hardcodes its own RM list (`RMPage.tsx:21`, `AVAILABLE_RMS = ["Rajesh Kumar", "Priya Singh", "Amit Patel", "Sneha Gupta"]`), which has no relation to any backend data, so a manual re-assign can write a name the backend has never seen.
- `RMPage.tsx:115` falls back to `"Auto"` when marking a lead converted, matching the backend placeholder.
- The RM endpoints (`rm_routes.py`) take the RM name from the URL and have no auth (§4), so nothing ties an RM's identity to the leads they can see. Combined with the Title-case classification bug (§8.1), the RM Control Desk shows no HOT leads even after assignment.
- `ASSIGN_RM` worker job is never enqueued (§1.3).

### 10.4 WARM → WhatsApp — likely failing in sandbox; several concrete causes

The recollection that the sandbox "is not working" is plausible and has identifiable causes in the code (actual Twilio-side state could not be verified from the repo):

- **Sandbox config is unvalidated and inconsistent.** `config.py:59` defaults `twilio_whatsapp_from` to the placeholder `"+919999999999"`, and `.env.example:18` uses `whatsapp:+1234567890`. The Twilio sandbox sender is a fixed Twilio number, and each recipient must first opt in by sending the join code to it. Nothing in the code, `instructions.txt` or the README mentions this, and there is no startup check. A lead who hasn't joined gets a Twilio error (63016/63015-class), which `_send_via_twilio` re-raises (`whatsapp_service.py:321-322`).
- **Business-initiated free-form messages are not allowed outside sandbox.** `send_warm_follow_up` sends plain text as the first message. In production WhatsApp requires a pre-approved template for the first outbound message; this design would need Content-Template SIDs (`content_sid`) to work off-sandbox.
- **Failures are retried into the dead-letter queue with no fallback.** `_process_send_whatsapp` raises on failure (`call_worker.py:194-195`) → retry/DLQ; the lead is never marked as "WhatsApp failed", so the dashboard shows no sign of it.
- **The `message` and `phone` fields queued at `webhook_routes.py:178-184` are ignored** — the worker re-reads the phone from the DB and picks a template by language, so the queued text is dead data.
- **Inbound reply path is fragile.** `whatsapp_routes.py:49` does an exact-match `get_lead_by_phone(clean_phone)` (`repository.py:152-157`). Twilio sends `+91…`; if leads were uploaded as `98…` or with spaces/dashes (the CSV path does no normalization, §5), the lead is "not found" and the message is silently ignored. The inbound webhook also has no signature check (§4).
- **The setup docs point the sandbox at the wrong webhook (most likely root cause of "warm replies don't work").** `Backend/README.md` §7 tells the operator to set the Twilio sandbox *"When a message comes in"* URL to `/api/webhook/twilio/whatsapp` — the canned-reply stub — not `/api/webhook/whatsapp`, the LLM handler for WARM leads (`whatsapp_routes.py`). Following the docs, every reply from a WARM lead gets the fixed text "A Relationship Manager will be in touch shortly" and the contextual LLM reply never runs. The doc also quotes a different reply string ("Thanks for messaging Sambhaash AI...") than the code returns, so it predates the current stub.
- **Duplicate/orphan inbound handler.** `webhook_routes.py:473-483` (`/api/webhook/twilio/whatsapp`) is a canned-reply stub that competes with the real LLM handler at `/api/webhook/whatsapp`; whichever URL is configured in the Twilio console decides which one runs, and the stub never checks the lead or replies contextually.
- Language-template fallbacks and the unused `hot_reminder_hi` template: see §3.

### 10.5 COLD — the score is saved, but the lead loops back into the call queue (new, high-impact)

> **FIXED on `fix/remediation`** (`webhook_routes.py:161-167`): COLD leads are now set to `FOLLOW_UP` instead of `NEW`, so the call initiator (which only selects `NEW`) no longer re-dials them. The live DB enum `leadstatus` already contained `FOLLOW_UP`, so no migration was needed. Verified with a stubbed repository: COLD → `FOLLOW_UP` (no RM, no WhatsApp), WARM → `INTERESTED` (+ WhatsApp job), HOT → `INTERESTED` (+ RM assignment). Still open in this section: no nurture/retry schedule exists for `FOLLOW_UP` leads, and the description below is kept as the original finding.

The note said COLD is "just saving in db". Checked: the `lead_scores` row *is* saved, but the surrounding logic is wrong:

- `webhook_routes.py:164` sets lead status to `LeadStatus.NEW` for COLD (`INTERESTED` only for HOT/WARM). `CallInitiator.find_and_call_new_leads` (`call_initiator.py:108-112`) selects every `NEW` lead every 30 s (`run_worker.py:69`). **A COLD lead — someone who said "no" — is therefore re-dialed on the next scheduler cycle, and again after every call, indefinitely.** The `REJECTED` comment at `call_initiator.py:215` ("so it doesn't infinitely loop") shows this hazard was considered for failures but not for COLD.
- `Backend/DOCS/AUTOMATIC_CALL_SETUP.md` documents this as intended ("COLD: Remains NEW, retry call later") but contradicts itself two sections earlier ("CONTACTED → INTERESTED/REJECTED"). The code follows the "stay NEW" version, and "later" is not implemented: there is no delay, cap or backoff, only the 30 s poll. `MESSAGING_WORKER_GUIDE.md` gives a third answer ("COLD: Archive for future campaigns"), which also does not exist.
- There is no `COLD`/`DO_NOT_CALL`/cooldown status in `LeadStatus` (`models.py:28-34`: NEW, CONTACTED, INTERESTED, CONVERTED, REJECTED, FOLLOW_UP), no retry cap, and no `last_contacted_at` check.
- Beyond the loop: no nurture path exists (no delayed follow-up, no drip), and `FOLLOW_UP` is defined but never set anywhere.
- Repeated auto-dialing of people who declined is also a compliance risk (DND/TCPA-style rules) for a telecalling product.

### 10.6 Future plan — per-RM CRM dashboard (not implemented; feasibility notes)

Confirmed that only an admin-facing view exists today. What already helps: `rm_assignments` table, `GET /api/rm/{rm_name}/queue`, `/dashboard` stats, `mark_lead_converted`, and a Supabase-JWT `get_current_user` that already exposes `user.role` (`api/auth.py:58`, `"role": user.role`). What is missing: an RM user/role model linking a login to an `rm_name`, auth on `rm_routes.py`, a scoped frontend route, and real allocation (§10.3). This is a new feature, so it is listed by name only in the README Future Scope.

---

## 11. Documentation vs. code drift

The written docs describe a system that differs from the code in many places. Docs checked: `Backend/README.md`, `Backend/DOCS/AUTOMATIC_CALL_SETUP.md`, `MESSAGING_WORKER_GUIDE.md`, `PHASE_2A_GUIDE.md`, root `README.md`, `instructions.txt`. `Frontend/README.md` is empty (0 bytes). Items are grouped by the claim being made; each was verified in the code.

### 11.1 Docs describe features that are not what runs

| Doc claim | Where | Reality |
|---|---|---|
| "LLM: Orchestrator processes intent + objections"; Phase 2A: Orchestrator merges KB context with RAG-engine results | `AUTOMATIC_CALL_SETUP.md` step 6, `PHASE_2A_GUIDE.md` "Updated Orchestrator" | The live path is the LangGraph stub (§1.2); `Orchestrator`, `CallManager.process_turn(kb_context=...)` and the merge code are never executed. |
| Scoring: "Interest: extracted from conversation; Engagement: how responsive; Sentiment: tone" | `AUTOMATIC_CALL_SETUP.md` step 8 | Hardcoded 70/70/70 or a keyword override (§1.3, §10.2). |
| "TTS generates AI response in same language" | `AUTOMATIC_CALL_SETUP.md` step 6 | Always English (§3). |
| "10 languages" / Sarvam multilingual | root `README.md` | Detection covers 3 labels, prompts are English-only (§10.1). |
| KB search is "Semantic similarity via pgvector", "GPU-accelerated similarity search", `min_score: 0.3` threshold | `PHASE_2A_GUIDE.md` "Search Parameters", "Performance Optimization" | Most-recent-N rows with a fake 0.8 score; threshold unused (§2). |
| "If KB service fails: falls back to RAG engine only" | `PHASE_2A_GUIDE.md` "Error Handling" | The RAG engine's retrieval returns `[]` (§1.2), so the "fallback" is no context at all. |
| "Assign to RM ... `/api/rm/queue`"; "Auto-assign" | `AUTOMATIC_CALL_SETUP.md` step 9, `Backend/README.md` endpoints | Endpoint is `/api/rm/{rm_name}/queue`; the assignment is a fixed placeholder name (§10.3). |
| "Scoring Engine → Queues ASSIGN_RM / RM notification WhatsApp" | `MESSAGING_WORKER_GUIDE.md` examples 2, "Integration workflow" | Nothing enqueues `ASSIGN_RM` (§1.3), and no RM notification exists (§10.3). |
| "Instantly trigger a live handoff to a Relationship Manager" | root `README.md` lifecycle step 5 | No `<Dial>`/transfer anywhere (§10.3). |
| "LangGraph evaluates the entire transcript's sentiment and intent" | root `README.md` lifecycle step 5 | Only the last user message is scored (§10.2). |

### 11.2 Docs would make an operator do the wrong thing

- **Sandbox webhook URL is wrong** — see §10.4 (points at the stub, not the LLM handler).
- **`hot_reminder` example fails.** `MESSAGING_WORKER_GUIDE.md` example 2 enqueues `message_type: "hot_reminder"`; `_process_send_whatsapp` (`call_worker.py:176-192`) only handles `warm_follow_up`/`conversion`/`custom` and raises `ValueError("Unknown message type")`, sending the job to retries and then the DLQ. Only a `hot_reminder_hi` *template* exists, never reachable (§3).
- **`python run_worker.py --workers=5`** (same guide, "Run multiple workers") — `run_worker.py` has no argument parsing; the flag is silently ignored. Running several instances also multiplies the non-atomic `dequeue_job` duplicate-processing race (§5).
- **Wrong start commands.** `Backend/README.md` gives `uvicorn app.main:app` (no `app` package exists) in one place and `uvicorn Backend.main:app` in another; the real entry is `main:app` from `Backend/` (as in the Dockerfile and root README).
- **Wrong import paths.** `MESSAGING_WORKER_GUIDE.md` imports `from backend.worker...` / `backend.services...` (lowercase `backend`), which do not exist; copy-pasting any example fails with `ModuleNotFoundError`.
- **Wrong env file.** `Backend/README.md` says config is loaded from `Backend/env` ("ignored by git"); `config.py:17` reads `.env`. The env-var list in that README (`OPENAI_API_KEY`, `WHATSAPP_BUSINESS_ACCOUNT_ID`, `WHATSAPP_TOKEN`) does not match `config.py`; the live code needs `GROQ_API_KEY`, `HF_API_KEY`, `SARVAM_API_KEY`, `TWILIO_WHATSAPP_FROM`. `AUTOMATIC_CALL_SETUP.md`'s pre-run checklist likewise asks for an OpenAI key that the code never uses.
- **Documented endpoints that 404.** `Backend/README.md` lists `GET /ready` (not defined; `health.py` is unmounted, §5), `POST /api/call/start`, `POST /api/webhooks/twilio` (actual: `/api/calls/outbound`, `/api/webhook/twilio/...`), and `/api/rm/{id}/assign` (actual: `POST /api/rm/assign`). `AUTOMATIC_CALL_SETUP.md` also references `GET /api/rm/leaderboard` (exists) but without noting it is unauthenticated (§4).

### 11.3 Technology stack described inconsistently across docs

| Item | Root README | `Backend/README.md` | `PHASE_2A_GUIDE.md` | Code |
|---|---|---|---|---|
| Embeddings | Hugging Face | OpenAI `text-embedding-3-small` | "all-MiniLM-L6-v2, local, no API key needed" | Hugging Face **cloud** Inference API, needs `HF_API_KEY` (`embedder.py:4,25,40-43`), 384-dim |
| STT | Groq Whisper | OpenAI Whisper | — | Groq-hosted Whisper via OpenAI SDK (`whisper_service.py`) |
| LLM | "Llama 3 (8B)" | "Groq (mixtral-8x7b)" | — | `llama-3.3-70b-versatile` hardcoded in `orchestration/state.py:11-15`; `config.py:46` default `llama3-8b-8192` is not what the live path uses |
| Queue | Redis task queue | "Redis + RQ/Celery" | — | Custom `QueueManager` on a sync `redis` client; no RQ or Celery installed (§5, §7) |
| Python | 3.9+ | 3.12+ | — | `instructions.txt` says 3.10+; `Dockerfile:1` builds on `python:3.11-slim` — three different minimums documented, 3.11 actually deployed |

### 11.4 Data the docs say is logged, but isn't (or is always empty)

`AUTOMATIC_CALL_SETUP.md` "Database Logging" claims each table is populated. Checked against writers:

- **`objections_log`** — the table and `Repository.create_objection` exist, but nothing ever calls `create_objection` (grep-confirmed). The table is always empty and "Objections detected during call / Resolution status" is never recorded (the objection-detection code lives in the dead `Orchestrator`).
- **`call_sessions.duration_seconds` and `call_sessions.classification`** — `update_call_session` accepts both, but the only two callers (`webhook_routes.py:95` and `kb_context_injection.py:258`) pass only `conversation_history` / `kb_usage_log`. Duration stays `0` and the session's own classification stays unset, so the WhatsApp/summary text at `call_worker.py:246` prints "Duration: 0s" on every call, and session-level classification cannot be queried.
- **`call_sessions.conversation_history`** — documented as `{user, ai, language, timestamp}`; that is the turn-dict shape that collides with the checkpointer's format (§1.1) and that the frontend and scoring engine read with different key names (§1.3, §8.2). The docs describe one of three incompatible shapes without flagging the conflict.
- **`kb_usage_log`** — written by `_log_kb_usage` (`kb_context_injection.py:246`), which does `json.loads(session.get("kb_usage_log", "[]"))`. Whether this works depends on whether the DB driver returns JSON columns as strings; if it returns an already-parsed list, `json.loads` raises `TypeError`, which the surrounding `except` swallows, so no usage would ever be logged. Not verified against the live database; worth a one-line test.

### 11.5 Stale structure, orphaned references, and ownership text

- `Backend/README.md` is two documents concatenated: a team-architecture doc ("Person 1–4", "Person 4 (YOU)") followed by a "Person 1 Runbook", with contradictory instructions (see §11.2). It describes a hackathon team split rather than the current code.
- It lists `docs/architecture.md` and `docs/flow.md` (the real folder is `DOCS/` and contains neither), and lists `utils/logger.py`, `audio_utils.py`, `text_utils.py`, `scripts/ingest_appendix.py` as implemented — all are empty files (§6). It omits modules that exist and matter: `orchestration/`, `kb_analytics_routes.py`, `admin_routes.py`, `queue_routes.py`, `summary_routes.py`, `public_routes.py`, `whatsapp_routes.py`, `call_recording_service.py`.
- The runbook's "Known prototype constraints" (§9) says the Person 2 handoff "is currently logging payload (not yet queue/API integrated)". It has since been integrated (via LangGraph) and the note is out of date, and the runbook's troubleshooting steps (§6 there) tell operators to look for a `Person 1 payload ready` log line, which no longer exists anywhere in the code (grep-confirmed), so that check can never succeed.
- `PHASE_2A_GUIDE.md` contained a real Supabase project URL in its configuration example. It is a project identifier rather than a secret, but it tied public docs to a specific project; it has been replaced with the placeholder `https://your-project.supabase.co`. The old URL remains in git history if that project ever needs to be rotated.
- `PHASE_2A_GUIDE.md` "Next Phases" (2B–3) list work that is already partly present (call recording, auto-scoring) or was superseded, so the roadmap no longer reflects the repo.
- `Frontend/README.md` is empty; `instructions.txt` is the only frontend setup doc, and root `README.md` uses `source venv/Scripts/activate` (Windows path) as the primary activation line for a macOS/Linux flow.

### 11.6 What to do once the code is fixed

This section is the checklist of doc edits the code fixes will require, so the docs are updated together with the fixes instead of drifting again: rewrite `Backend/README.md` as one document; fix the sandbox webhook URL; correct the stack table (§11.3) in every doc that repeats it; delete or mark `MESSAGING_WORKER_GUIDE.md` examples that use unimplemented message types; and only then update the root `README.md` feature claims (multilingual, RAG, live handoff, scoring) to match what actually ships.

---

## 12. Runtime verification (run locally with real `.env` files)

The project was installed and started locally to confirm the static findings. Setup: macOS, Python 3.14.7 (project targets 3.11), fresh venv, `pip install -r requirements.txt`, API started with `MODE=production` (skips the ngrok tunnel; `.env` unchanged), worker **not** started. Only read-only GET requests and read-only SQL `SELECT`s were run. The Docker daemon was not running, so Redis was unavailable.

### 12.1 What works

- **Frontend:** `npx tsc -b` passes with zero errors; `npm run build` succeeds (single 1.13 MB JS chunk, over Vite's 500 kB warning).
- **Backend imports:** `config`, `orchestration.*` (including the hand-written checkpointer against the newest LangGraph 1.2.12 / langgraph-checkpoint 4.2.0), `webhook_routes` and `main` all import cleanly. So the unpinned-version risk in §7 has not broken imports yet; it is still untested at call time.
- **Startup:** the API boots, the Supabase pool connects, `GET /health` → 200, `/docs` → 200.
- **DB-backed reads work:** `GET /api/rm/Auto/queue` → 200 (empty), `GET /admin/kb/analytics/effectiveness` → 200.

### 12.2 New bugs found at runtime

- **`GET /api/rm/leaderboard` returns HTTP 500** (`function round(double precision, integer) does not exist`). `repository.py:698-701` and `722-725` cast to `::float` before `ROUND(..., 2)`; PostgreSQL only has `round(numeric, int)`, so the cast must be `::numeric`. The identical expression is in `get_rm_stats` (`repository.py:693-703`) which backs `GET /api/rm/{rm_name}/dashboard`, so that endpoint should fail the same way (same query pattern; not called during this run). The RM leaderboard and RM performance dashboard are therefore broken in addition to §10.3.
- **`GET /api/queue/stats` returns HTTP 500** when Redis is down (`Error 61 connecting to localhost:6379`) instead of a clear "queue unavailable" response; the raw connection error is returned to the caller (compare §4, leaked internal errors). More importantly, `docker-compose`/README both assume Redis is available, and nothing in the API startup checks for it, so the API reports healthy while the queue is dead.
- **Ngrok opens automatically in the default dev config.** With `MODE=development` and an `NGROK_AUTH_TOKEN` (the documented setup), starting the API publishes a public tunnel to an API whose call/WhatsApp trigger endpoints have no authentication (§4). Nothing warns about this; the only mitigation is running with `MODE=production` locally.

### 12.3 Static findings confirmed against the live server / DB

| Finding | Evidence |
|---|---|
| `/ready` documented but missing (§11.2) | `GET /ready` → 404 |
| Call Recordings router never mounted (§5) | `GET /admin/recordings` → 404 |
| KB analytics presents invented numbers (§4) | `effectiveness` with **0** calls analysed still returns `avg_relevance_score: 0.75` |
| `call_sessions.duration_seconds` never written (§11.4) | 8 real sessions in the DB, `SUM(duration_seconds) = 0` |
| COLD leads are saved but the lead is looped/reset (§10.5) | 3 `lead_scores` rows, all `COLD`; leads currently `CONTACTED` ×3 and `REJECTED` ×2, none `NEW` |
| RM allocation is free-text (§10.3) | `rm_assignments` holds two manual names ("Sneha Gupta", "Amit Patel"), none from the `"Auto"` default, so those came from the frontend's hardcoded RM list |
| Protected route behaves as designed | `GET /api/leads` without a token → 401 (the only router that enforces auth, §4) |

### 12.4 Environment notes for working on the project

- **Python version:** only 3.14 was available locally, but the Dockerfile targets 3.11 (§11.3). It installed and imported fine, but use 3.11 for any behaviour you intend to ship.
- **Never start `run_worker.py` while `NEW` leads exist** unless you intend real calls: the call initiator dials every `NEW` lead within 30 s (§10.5). At the time of this check there were no `NEW` leads, so starting it would not have called anyone, but creating a lead via the API or CSV would.
- **The `.env` keys present are complete for the core flow** (Supabase, Groq, HF, Sarvam, Twilio incl. WhatsApp from-number, Redis, ngrok). Not set and worth adding: `TWILIO_WEBHOOK_BASE_URL` (otherwise webhooks default to `http://localhost:8000`, which Twilio cannot reach unless the ngrok auto-detect works, and that auto-detect reads the wrong JSON key, §5), and `DEFAULT_RM_NAME` if you don't want `"Auto"`.
- **Supabase is a shared, live database** (real leads and sessions exist). Point a separate Supabase project at development before running fix branches that write data.
