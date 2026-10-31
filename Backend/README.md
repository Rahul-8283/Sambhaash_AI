# Sambhaash AI — Backend

FastAPI service and background worker for outbound voice-AI lead qualification.
Twilio places the call, Groq Whisper transcribes, a LangGraph graph writes the
reply, Sarvam speaks it, and the outcome (HOT / WARM / COLD) drives RM
assignment or a WhatsApp follow-up.

- Repository overview and architecture diagram: [`../README.md`](../README.md)
- What works and what doesn't, with `file:line` references: [`../CODE_AUDIT.md`](../CODE_AUDIT.md)
- Deeper guides: [`DOCS/`](DOCS/)

## Stack (as implemented)

| Concern | Implementation |
|---|---|
| API | FastAPI, Python 3.11 (the Dockerfile target) |
| Telephony | Twilio Voice (`<Record>` → webhook → `<Play>` loop) and Twilio WhatsApp |
| STT | Groq-hosted Whisper through the OpenAI SDK, model `STT_MODEL_NAME` (default `whisper-large-v3-turbo`) |
| LLM | Groq via `langchain-groq`, model `LLM_MODEL_NAME` (default `qwen/qwen3.8-27b`) |
| Orchestration | LangGraph: intent routing → rag / objection / pitch → outcome (keyword heuristics) |
| TTS | Sarvam `bulbul:v3`, each reply split in two and synthesized in parallel |
| Embeddings | `all-MiniLM-L6-v2` (384-dim) run locally with fastembed/ONNX, no API key |
| Scoring | `services/scoring` (intent / engagement / sentiment keyword scorers) |
| Database | Supabase Postgres via `asyncpg`, raw SQL in `services/database/repository.py` |
| Queue | Redis, hand-rolled priority queues in `worker/queue_manager.py` |

## Layout

```
api/            routers, Supabase JWT auth (auth.py), Twilio signature check, rate limit
orchestration/  LangGraph graph, nodes, outcome heuristics, history rebuild
services/
  database/     asyncpg client, repository, SQLAlchemy models (DDL + enums only)
  llm/          embedder, KB context injection, Groq client, summary generator
  stt/          Whisper service, language detector
  tts/          Sarvam service, audio formatter
  telephony/    Twilio client, CallManager (TTS step)
  messaging/    WhatsApp templates and sender
  scoring/      scoring engine and calculators
worker/         call initiator (dials NEW leads) and Redis job worker
scripts/        init_db.py, migrate.py, migrations/
tests/          pytest suite (no network, DB, Redis or Twilio needed)
```

## Run it locally

```bash
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                 # then fill in the keys below
docker run -d --name sambhaash-redis -p 6379:6379 redis:alpine

python scripts/init_db.py            # creates tables on a NEW database
python -m uvicorn main:app --reload  # API on :8000, Swagger at /docs
python run_worker.py                 # separate process: dialer + job worker
```

Start the API before the worker: in `MODE=development` the API opens the ngrok
tunnel and writes its URL to `ngrok_url.json`, which the worker reads.

**Safety**

- Supabase is a shared, live database in this project. Point development at a
  separate Supabase project before running anything that writes.
- The worker dials every `NEW` lead within 30 seconds. Do not start it while
  `NEW` leads exist unless you intend real calls.
- Twilio trial accounts can only call numbers under *Verified Caller IDs*, and
  play a trial message that needs a keypress before the call connects.
- `uvicorn --reload` restarts the server when a file changes, which drops a call
  that is in progress. Do not edit code during a test call.
- The ngrok tunnel is opt-in: it opens on startup only with `MODE=development`,
  `ENABLE_NGROK=true` and an `NGROK_AUTH_TOKEN`.

## Environment

Loaded from `Backend/.env` by `config.py`. Unset secrets fall back to the
sentinel `sk-test-default`, so a missing key degrades at call time rather than
crashing startup.

| Variable | Purpose |
|---|---|
| `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_BUCKET_NAME` | database, JWT verification, KB file storage |
| `GROQ_API_KEY` | Whisper and the reply LLM |
| `LLM_MODEL_NAME`, `LLM_MAX_TOKENS`, `STT_MODEL_NAME` | model choice and reply cap (defaults above, 160 tokens) |
| `SARVAM_API_KEY` | TTS |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER` | voice |
| `TWILIO_WHATSAPP_FROM` | WhatsApp sender (`whatsapp:+14155238886` for the sandbox) |
| `TWILIO_WEBHOOK_BASE_URL` | public URL Twilio calls back (ngrok or the deployed host) |
| `TWILIO_VALIDATE_SIGNATURES` | keep `true` except for local debugging |
| `REDIS_URL` | queue |
| `NGROK_AUTH_TOKEN`, `MODE`, `ENVIRONMENT` | tunnel and mode |
| `CORS_ORIGINS`, `TRUSTED_HOSTS` | comma-separated allow-lists |
| `PUBLIC_RATE_LIMIT_MAX`, `PUBLIC_RATE_LIMIT_WINDOW_SECONDS` | landing-form limit (5 per 600 s per IP) |
| `EMBEDDING_CACHE_DIR` | where the ONNX embedding model is cached |
| `ENFORCE_CALL_WINDOW` | automatic dials (new and retry) only 09:00-21:00 IST; false for local testing |
| `NURTURE_ENABLED`, `NURTURE_MAX_ATTEMPTS`, `NURTURE_COOLDOWN_HOURS`, `CALL_WINDOW_START_HOUR`/`END_HOUR` | retry unanswered leads (off by default), IST calling hours |
| `LIVE_TRANSFER_ENABLED`, `LIVE_TRANSFER_TIMEOUT_SECONDS` | bridge a HOT call to the RM's phone (off by default; falls back to hangup) |
| `RM_ROSTER` (`Asha:+9198...,Ravi`), `DEFAULT_RM_NAME`, `DEFAULT_COUNTRY_CODE`, `MAX_TURNS_PER_SESSION` | assignment name, phone normalization, call length |

`HF_API_KEY` is no longer used.

## How a call works

1. The worker picks a `NEW` lead, creates a `call_sessions` row and asks Twilio
   to call, with `session_id` and `lead_id` in the webhook URL.
2. Twilio hits `POST /api/webhook/twilio/voice` (signature-checked), which
   answers with a greeting and a `<Record>`.
3. Each recording lands on `POST /api/webhook/twilio/recording`:
   Whisper → language detection → KB lookup → LangGraph (with the call so far
   rebuilt from `call_sessions.conversation_history`) → turn saved while TTS
   renders → `<Play>` the reply and `<Record>` again. The next-turn URL carries
   the session ids, so a restart does not lose the call.
4. On a clear yes/no from the caller, or `MAX_TURNS_PER_SESSION`, the call is
   scored by `ScoringEngine` and ended. A clear HOT/COLD keyword wins over the
   engine's classification.
5. HOT → assigned to the least-loaded RM in `RM_ROSTER` (or `DEFAULT_RM_NAME` when no roster) and, if that RM has a number, notified on WhatsApp; WARM → WhatsApp follow-up job; COLD →
   status `FOLLOW_UP` (never re-dialled). A summary job is always queued.

Language: the language established on the call hints Whisper from turn 2 on,
very short replies keep it, and the detected language is stored on the lead.

## API

Dashboard routes require a Supabase JWT (`Authorization: Bearer …`) unless noted.

| Prefix | Notes |
|---|---|
| `/api/leads` | CRUD, search, CSV/JSON batch upload; `GET /{id}` includes sessions, score history, objections, notes |
| `/api/rm` | `/{rm}/queue`, `POST /assign`, `POST /{rm}/{lead}/complete`, `/{rm}/dashboard`, `/leaderboard` |
| `/api/calls` | `POST /outbound`, `POST /whatsapp`, `GET /status/{sid}` |
| `/api/queue` | `/stats`, `/dlq`, `POST /dlq/{job}/retry` |
| `/api/v1/summaries` | generated call summaries |
| `/admin/kb` | `POST /upload`, `/documents`, `/search`, `/stats` |
| `/admin/kb/analytics` | `/effectiveness`, `/call/{session}`, `/document-impact/{doc}` |
| `/admin/recordings` | recordings, transcription, statistics |
| `/api/public/leads` | no auth, rate limited per IP |
| `/api/webhook/twilio/*` | `voice`, `recording`, `status`, `audio/{sid}` (no auth, Twilio fetches it), `whatsapp` |
| `/api/webhook/whatsapp` | inbound WhatsApp replies for WARM leads (LLM answer) |
| `/health` | liveness |

Point the Twilio WhatsApp sandbox "When a message comes in" at
`/api/webhook/whatsapp`. (The old canned-reply route under
`/api/webhook/twilio/whatsapp` was removed.)

## Queue

`JobType`: `send_whatsapp` (`warm_follow_up`, `conversion`, `custom`) and
`send_summary`. Jobs retry with exponential backoff (1 s, 2 s, 4 s) and then
land in the dead-letter queue, which `/api/queue/dlq` lists and can retry.

## Database

Tables: `leads`, `call_sessions`, `lead_scores`, `objections_log`, `documents`,
`knowledge_base`, `rm_assignments`, `call_recordings`. `knowledge_base.embedding`
is JSON text and similarity is computed in Python, not with pgvector operators.

Schema changes live in `scripts/migrations/` and are idempotent:

```bash
python scripts/migrate.py            # list pending files
python scripts/migrate.py --apply    # run them against DATABASE_URL
```

`001_rm_conversion_notes.sql` and `002_lead_notes.sql` are not yet applied to
the shared database; saving notes answers 503 until `002` is.

## Tests

```bash
pip install -r requirements.txt
pytest
```

No network, database, Redis, Twilio or Groq is needed: the suite covers outcome
and language handling, scoring, TTS splitting, WhatsApp templates, the embedder's
failure mode, rate limiting, Twilio signatures, KB analytics, and whole calls
through the recording webhook with fakes for every external service.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Every turn says "Sorry, I could not process your input" | the Groq model is unavailable to your key (`404 model_not_found`); set `LLM_MODEL_NAME` to one from `GET /openai/v1/models` |
| KB never used, `kb_available: false` | embedding model failed to load; check the startup log and `EMBEDDING_CACHE_DIR` |
| Webhooks return 403 | wrong `TWILIO_AUTH_TOKEN`, or the public URL differs from `TWILIO_WEBHOOK_BASE_URL` |
| Webhooks return 503 | auth token unset, or the server was reloading |
| Call connects then ends in ~15 s | Twilio trial keypress prompt, or the recording webhook failed (see Twilio Console → Monitor → Alerts) |
| `/api/queue/stats` 500 | Redis not running |
| WARM lead gets a canned reply on WhatsApp | sandbox pointed at the wrong webhook (see API section) |
