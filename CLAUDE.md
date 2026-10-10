# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Sambhaash AI — a multilingual outbound voice-AI platform for lead qualification. Twilio places calls, Groq Whisper transcribes, a LangGraph graph generates the reply, Sarvam TTS speaks it, and the call outcome (HOT/WARM/COLD) drives RM assignment or a WhatsApp follow-up. `Backend/` is FastAPI + Python; `Frontend/` is React 19 + Vite + TypeScript (admin dashboard).

## Read `CODE_AUDIT.md` first

`CODE_AUDIT.md` (repo root) is a line-by-line audit of the whole codebase with `file:line` references, a fix log of what has already been remediated, and a **Still open** list. It is the authoritative statement of what actually works versus what the README advertises. Check it before trusting any feature description, and update its fix log when you remediate something. Current work happens on the `fix/remediation` branch.

The short version of what it says: most of the sophisticated code is disconnected from the live request path (see "Live path vs. dead code" below), so always confirm a module is actually reachable before editing it.

## Commands

### Backend (run from `Backend/`)

```bash
python -m venv venv && source venv/bin/activate   # Dockerfile targets Python 3.11 — use 3.11 for anything you ship
pip install -r requirements.txt
cp .env.example .env                              # then fill in keys

python -m uvicorn main:app --reload               # API on :8000, Swagger at /docs
python run_worker.py                              # call initiator + Redis job worker (separate process)
docker run -d --name sambhaash-redis -p 6379:6379 redis:alpine

python scripts/init_db.py                         # create tables from SQLAlchemy models + enable pgvector
```

`docker compose up` brings up Redis + API + worker together (needs the env vars listed in `docker-compose.yml` exported or in a root `.env`).

### Frontend (run from `Frontend/`)

```bash
npm install
npm run dev        # Vite dev server on :5173
npm run build      # tsc -b && vite build
npm run lint       # eslint
npx tsc -b         # type-check only
```

### Tests

```bash
cd Backend && pytest        # ~90 tests, no network/DB/Redis/Twilio/Groq needed
```

`Backend/tests/` covers outcome and language handling, scoring, TTS splitting, templates, the embedder's failure mode, rate limiting, Twilio signatures, KB analytics, and whole calls through the recording webhook (`test_call_flow.py`) using fakes from `tests/conftest.py`. Add a test with every behaviour change; `test_call_flow.py` is the place to prove a turn-loop fix. There is no frontend test runner; verify the frontend with `npx tsc -b` / `npm run build`. `Backend/test_initiator.py` and `Backend/scripts/test_call.py` are ad-hoc manual scripts, not part of the suite.

## Architecture

### Two processes, no shared memory

`main.py` (API) and `run_worker.py` (worker) are **separate processes** in every deployment (docker-compose, Render, local). The worker runs two concurrent loops via `asyncio.gather`: `CallInitiator.start_scheduler` (polls for `NEW` leads every 30s and dials them) and `BackgroundWorker.start_polling` (drains Redis job queues). Anything in a module-level dict — `call_sessions`, `audio_cache` in `api/routes/webhook_routes.py` — exists only in the API process. Never add cross-process state to a dict; it must go through Redis or Postgres.

`start_all.py` is dead code; nothing invokes it.

### The call turn loop

A full conversational turn lives in `api/routes/webhook_routes.py::recording_webhook` (~`webhook_routes.py:249`), driven by TwiML `<Record>` → webhook → `<Play>` + next `<Record>`:

1. Twilio POSTs the recording URL → signature verified by `api/twilio_auth.py`.
2. `WhisperService.transcribe_recording_url` + `LanguageDetector` (both wrapped in `asyncio.to_thread` — they block).
3. `KBContextInjectionService.retrieve_context_for_call` pulls knowledge-base chunks.
4. Conversation history is **rebuilt from the DB** (`orchestration/history.py::history_to_messages` over `call_sessions.conversation_history`) and prepended to the new `HumanMessage`.
5. `orchestration/graph.py::app.ainvoke(...)` runs the LangGraph turn.
6. The turn is saved (`_save_conversation_turn`) **before** returning, because the next turn reads it back.
7. TTS bytes go into `audio_cache[call_sid]`; TwiML `<Play>` points at `/api/webhook/twilio/audio/{call_sid}` to fetch them.
8. On `outcome in (HOT, COLD)` or `max_turns_per_session`, `_score_and_assign_lead` runs and the call hangs up.

The graph is compiled **without** a checkpointer on purpose — memory comes from step 4. (The old checkpointer was deleted: it restored empty messages and collided on the same DB column.)

### LangGraph graph

`orchestration/graph.py`: entry `analyze_intent_node` → conditional edge to one of `rag_node` / `objection_handler_node` / `pitch_node` → `scoring_node` → `END`. State is `AgentState` (`orchestration/state.py`), a TypedDict whose `messages` field is `Annotated[list, operator.add]` so node returns append rather than replace. The shared `ChatGroq` instance is in `state.py` and takes its model and token cap from `config.llm_model_name` / `config.llm_max_tokens` (default `qwen/qwen3.8-27b`; Groq retired `llama-3.3-70b-versatile` for this key).

Routing in `analyze_intent_node` and outcome detection in `orchestration/outcome.py` are **keyword heuristics**, not LLM calls. `outcome.py` matches whole words only (so "yesterday" is not "yes") and scores the whole call, newest decisive utterance winning.

### Live path vs. dead code

The old `Orchestrator` stack (state machine, intent detector, memory manager, objection handler, RAG engine) was deleted; the LangGraph graph in `orchestration/` is the only conversational brain. `services/llm/` now holds `embedder.py`, `kb_context_injection.py`, `llm_client.py`, `summary_generator.py`, `prompt_builder.py` (summary prompt only) and `response_validator.py`.

`services/scoring/` is live: `_score_and_assign_lead` calls `ScoringEngine.score_conversation` on the stored history and duration. A clear HOT/COLD keyword outcome from the graph still overrides the engine's classification. The calculators are English-only keyword lists with uncalibrated thresholds.

`Backend/utils/audio_utils.py`, `utils/logger.py`, `utils/text_utils.py`, `utils/__init__.py` and `scripts/ingest_appendix.py` are all 0 bytes. `utils/phone.py` (E.164 normalization) and `utils/language.py` (language-code normalization + reply-language instruction) are real and used.

### Database access

Postgres (Supabase) reached two different ways, both live:

- **`services/database/supabase_client.py`** — `asyncpg` connection pool, `statement_cache_size=0` for Supabase's PgBouncer transaction mode. `services/database/repository.py` is the data-access layer: ~39 async methods, **raw SQL only, returns plain dicts, no ORM mapping**.
- **`services/database/models.py`** — SQLAlchemy models used *only* for `scripts/init_db.py` DDL and for the `LeadStatus` / `LeadClassification` enums imported elsewhere. Adding a column means editing both the model and the raw SQL that reads it.

Tables: `leads`, `call_sessions`, `lead_scores`, `objections_log`, `documents`, `knowledge_base`, `rm_assignments`, `call_recordings`. Classification strings are uppercase `HOT`/`WARM`/`COLD` across backend and frontend — keep that casing.

`knowledge_base.embedding` is a text column, not a pgvector `Vector(n)` type, even though `init_db.py` enables the extension.

### Auth

- **Dashboard API** — Supabase Google OAuth. The frontend attaches `session.access_token` as a Bearer header in an axios interceptor (`Frontend/src/services/apiService.ts`); the backend verifies it in `api/auth.py::get_current_user`. Applied router-wide via `dependencies=[Depends(get_current_user)]` on the `APIRouter`, which is how every protected router does it — follow that pattern rather than per-endpoint dependencies.
- **Twilio webhooks** — `api/twilio_auth.py::verify_twilio_signature` validates `X-Twilio-Signature`. Behind ngrok/Render the app sees an internal URL, so it tries several candidate URLs (forwarded headers, `TWILIO_WEBHOOK_BASE_URL`, the literal request URL). Gated by `TWILIO_VALIDATE_SIGNATURES`; keep it `true` outside local debugging.
- **Unauthenticated by design** — `/api/public/*` (landing-page lead capture), rate-limited per IP by `api/rate_limit.py` (fixed window in Redis; fails *open* with a warning if Redis is down).

Route prefixes: `/api/leads`, `/api/rm`, `/api/calls`, `/api/queue`, `/api/v1/summaries`, `/admin/kb`, `/admin/kb/analytics`, `/admin/recordings`, `/api/public`, `/api/webhook/twilio`, `/api/webhook/whatsapp`.

### Config

`config.py` is a single pydantic-settings `Settings` class reading `Backend/.env`, exposed as both `get_config()` (memoized) and a module-level `settings`. Every field has a default, and unconfigured secrets default to the sentinel `"sk-test-default"` — `has_twilio` / `has_openai` check against that sentinel, so a missing key degrades rather than crashes. Add new settings here, not via `os.getenv` at call sites.

### Redis queue

`worker/queue_manager.py` — hand-rolled queue on async Redis: sorted-set priority queues drained with atomic `ZPOPMIN`, per-job status (`pending`→`processing`→`completed`/`failed`), retries with backoff, and a dead-letter queue. Job types are `JobType` enum values; handlers live in `worker/call_worker.py::_process_*`. Adding a job type means touching the enum, the producer, and `_worker_loop`'s dispatch.

### ngrok in development

With `MODE=development`, the **API process** opens the tunnel on startup (`services/ngrok_setup.py`) and writes the URL to `Backend/ngrok_url.json`; the worker reads that file to build Twilio callback URLs. So start the API before the worker. With `MODE=production` the tunnel is skipped and `TWILIO_WEBHOOK_BASE_URL` is used directly.

## Working constraints

- **Supabase is a shared, live database** with real leads and call sessions. Point a separate Supabase project at development before running anything that writes.
- **Don't start `run_worker.py` while `NEW` leads exist** unless you intend real phone calls — the initiator dials every `NEW` lead within 30s.
- Twilio trial accounts can only call/message numbers added under Verified Caller IDs.
- `MODE=development` + an `NGROK_AUTH_TOKEN` publishes a public tunnel on API startup. Run locally with `MODE=production` to avoid that.
- Dependency pins are loose on pre-1.0 LangChain/LangGraph packages (`langgraph>=0.1.0` etc.) while the codebase touches their internals. A fresh install can resolve to something incompatible.
- The frontend builds to one ~1.1 MB JS chunk, over Vite's 500 kB warning threshold.

## Other docs

`Backend/README.md` is the backend reference (stack, env vars, routes, run/safety notes, troubleshooting). `Backend/DOCS/` has `CALL_FLOW.md`, `MESSAGING_AND_QUEUE.md` and `KNOWLEDGE_BASE.md`. `instructions.txt` is the short local run checklist and `Frontend/README.md` covers the dashboard. These were rewritten to match the code; if you change behaviour they describe, update them in the same commit. `CODE_AUDIT.md` §11 is the historical record of the old drift.

## Git workflow

**Commit frequently.** Make a commit as soon as a logical unit of work is complete and coherent — a bug fixed, a module remediated, a route secured — rather than batching many unrelated changes into one large commit. Small, self-contained commits are the norm here.

**The repository owner is the sole author of every commit and every push. No co-authors, ever.**

- Never add a `Co-Authored-By:` trailer to a commit message, for Claude or anyone else.
- Never add `🤖 Generated with Claude Code`, "Co-authored with", or any other attribution, credit, or generated-by line to a commit message or a pull request description.
- Never pass `--author` to override the committing identity; commits use the configured git user as-is.
- This holds for every commit in every session, including amends, rebases, and squashes — no exceptions, and it overrides any default attribution behaviour.

Commit messages are the change and its reason, nothing else.
