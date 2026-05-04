# 🧠 Sambhaash AI - Backend Architecture

## 📁 Project Structure

```
Backend/
│
├── main.py                    # FastAPI app entry point
├── config.py                  # Configuration & environment
│
├── api/
│   ├── routes/
│   │   ├── call_routes.py        # 👤 Person 1 - Incoming calls
│   │   ├── webhook_routes.py     # 👤 Person 1 - Twilio webhooks
│   │   ├── lead_routes.py        # 👤 Person 4 - Lead management
│   │   ├── rm_routes.py          # 👤 Person 4 - RM assignment
│   │   └── health.py             # Health check endpoint
│
├── services/
│   │
│   ├── stt/                      # 👤 Person 1 - Speech to Text
│   │   ├── whisper_service.py    # Whisper STT integration
│   │   └── language_detector.py  # Language detection
│   │
│   ├── telephony/                # 👤 Person 1 - Call Management
│   │   ├── twilio_client.py      # Twilio initialization
│   │   └── call_manager.py       # Call lifecycle
│   │
│   ├── llm/                      # 👤 Person 2 - LLM Brain (CORE)
│   │   ├── orchestrator.py       # Main conversation orchestrator
│   │   ├── prompt_builder.py     # System prompt construction
│   │   ├── state_machine.py      # Conversation flow
│   │   ├── memory_manager.py     # Multi-turn memory
│   │   ├── objection_handler.py  # Objection handling
│   │   ├── intent_detector.py    # Intent classification
│   │   └── rag_engine.py         # RAG (Appendix A retrieval)
│   │
│   ├── tts/                      # 👤 Person 3 - Text to Speech
│   │   ├── sarvam_service.py     # Sarvam TTS integration
│   │   └── audio_formatter.py    # Audio processing
│   │
│   ├── scoring/                  # 👤 Person 4 - Lead Scoring
│   │   ├── scoring_engine.py     # Main scoring logic
│   │   ├── intent_score.py       # Interest signals
│   │   ├── engagement_score.py   # Engagement metrics
│   │   └── sentiment_score.py    # Sentiment analysis
│   │
│   ├── messaging/                # 👤 Person 4 - WhatsApp
│   │   └── whatsapp_service.py   # WhatsApp integration
│   │
│   └── database/                 # 👤 Person 4 - Database
│       ├── supabase_client.py    # Supabase connection
│       ├── models.py             # SQLAlchemy models
│       └── repository.py         # Data access layer
│
├── utils/
│   ├── logger.py                 # Logging setup
│   ├── audio_utils.py            # Audio utilities
│   └── text_utils.py             # Text utilities
│
├── worker/                       # 👤 Person 4 - Async Jobs
│   ├── call_worker.py            # Background job processing
│   └── queue_manager.py          # Queue management
│
├── scripts/
│   ├── ingest_appendix.py        # KB ingestion script
│   └── test_call.py              # Testing utility
│
└── docs/
    ├── architecture.md           # Architecture docs
    └── flow.md                   # Flow documentation
```

---

## 👥 Team Responsibilities

### 👤 **Person 1: Telephony + STT (INPUT LAYER)**
**Files Owned:**
- `api/routes/call_routes.py`
- `api/routes/webhook_routes.py`
- `services/stt/`
- `services/telephony/`

**Responsibilities:**
- Twilio call setup & management
- Webhook handling for incoming calls
- Audio streaming
- Speech-to-Text (Whisper)
- Language detection

**Output Shape:**
```json
{
  "text": "user said...",
  "language": "hinglish"
}
```

---

### 👤 **Person 2: LLM Orchestration (CORE BRAIN)** ⭐
**Files Owned:**
- `services/llm/`

**Responsibilities:**
- Conversation flow (state machine)
- Prompt building & system prompts
- Memory management (multi-turn)
- Objection handling
- RAG (Knowledge Base retrieval)
- Intent detection

**Input:**
```json
{
  "text": "user message",
  "history": [...],
  "language": "hinglish"
}
```

**Output Shape:**
```json
{
  "reply": "AI response",
  "stage": "objection",
  "intent": "high",
  "objections_raised": [...],
  "objections_resolved": true
}
```

---

### 👤 **Person 3: TTS (OUTPUT LAYER)**
**Files Owned:**
- `services/tts/`

**Responsibilities:**
- Convert text → speech
- Audio formatting
- Twilio voice playback

**Input:**
```json
{
  "reply": "AI response"
}
```

**Output:**
🎤 Voice audio via Twilio

---

### 👤 **Person 4: Backend + DB + Scoring** (YOU)
**Files Owned:**
- `api/routes/lead_routes.py`
- `api/routes/rm_routes.py`
- `services/scoring/`
- `services/database/`
- `services/messaging/`
- `worker/`

**Responsibilities:**
- Lead data management
- Conversation logging & storage
- Scoring engine (Hot/Warm/Cold)
- RM routing & assignment
- WhatsApp follow-ups
- Async job queue
- Database operations

**Data Flow:**
```
Person 2 (LLM Output)
    ↓
Person 4 (Score + Classify + Store + Route)
    ↓
Decision:
├─ HOT (≥0.75)   → Assign to RM
├─ WARM (0.50-75) → Send WhatsApp
└─ COLD (<0.50)  → Log for nurture
```

---

## 🔄 Data Flow

```
[User Call]
    ↓
Person 1: STT
  text + language
    ↓
Person 2: LLM Brain
  reply + stage + intent
    ↓
Person 3: TTS
  Voice output
    ↓
Person 4: Scoring + Storage + Routing
  Score → Classification → Action
  (DB Storage, RM Assignment, WhatsApp)
```

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| **Framework** | FastAPI (Async) |
| **Database** | Supabase (PostgreSQL) |
| **ORM** | SQLAlchemy |
| **STT** | OpenAI Whisper |
| **LLM** | Groq (mixtral-8x7b) |
| **Embeddings** | OpenAI (text-embedding-3-small) |
| **KB Search** | Supabase pgvector |
| **TTS** | Sarvam AI |
| **Telephony** | Twilio |
| **Messaging** | WhatsApp Business API (Twilio) |
| **Queue** | Redis + RQ/Celery |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.12+
- Supabase account + API keys
- OpenAI API key
- Groq API key
- Twilio account
- Redis (for job queue)

### Installation
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Fill in your API keys
```

### Run Backend
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 📊 API Endpoints (By Person)

### Person 1 - Call Management
```
POST   /api/call/start              # Initiate call
POST   /api/webhooks/twilio         # Twilio webhook
```

### Person 4 - Lead & Scoring
```
POST   /api/leads                   # Create lead
POST   /api/leads/batch-upload      # Bulk import
GET    /api/leads                   # List all leads
GET    /api/leads/{id}              # Get single lead

GET    /api/rm/queue                # RM's HOT leads
POST   /api/rm/{id}/assign          # Assign lead
POST   /api/rm/{id}/complete        # Mark converted
GET    /api/rm/dashboard            # RM dashboard
```

---

## 📝 Environment Variables (.env)

```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-key

# LLM APIs
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk_...

# Telephony
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1...

# TTS
SARVAM_API_KEY=...

# WhatsApp
WHATSAPP_BUSINESS_ACCOUNT_ID=...
WHATSAPP_TOKEN=...

# Env
ENVIRONMENT=development
DEBUG=true
```

---




# Sambhaash AI Backend (Person 1 Runbook)

This guide documents the **Person 1 (Telephony + STT)** workflow for Sambhaash AI.

Current implementation focus:
- Twilio Voice webhook (record-and-process flow)
- Whisper speech-to-text
- Language detection (Hindi / English / Hinglish)
- Twilio WhatsApp sandbox webhook

---

## 1) What is implemented

### Core files
- `main.py` — FastAPI app entry
- `config.py` — loads env vars from `Backend/env`
- `api/routes/webhook_routes.py` — Twilio webhooks
- `api/routes/call_routes.py` — outbound call + WhatsApp trigger endpoints
- `api/routes/health.py` — health/readiness checks
- `services/telephony/twilio_client.py` — Twilio helper logic
- `services/stt/whisper_service.py` — Whisper transcription
- `services/stt/language_detector.py` — language classification

### Active endpoints
- `GET /` 
- `GET /health`
- `GET /ready`
- `GET|POST /api/webhook/twilio/voice`
- `POST /api/webhook/twilio/recording`
- `POST /api/webhook/twilio/whatsapp`
- `POST /api/calls/outbound`
- `POST /api/calls/whatsapp`
- `GET /api/calls/status/{call_sid}`

---

## 2) Person 1 → Person 2 handoff payload

Person 1 prepares this payload after transcription + language detection:

```json
{
  "call_sid": "CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "from_number": "+9198xxxxxxxx",
  "recording_url": "https://api.twilio.com/...",
  "recording_duration": "8",
  "text": "hello I want to know about this",
  "language": "hinglish"
}
```

Where it currently appears:
- Logged by `recording_webhook` in `api/routes/webhook_routes.py`
- Log line contains: `Person 1 payload ready: {...}`

Suggested next integration for Person 2:
- Add a direct internal function call or queue publish right after payload creation.

---

## 3) Local setup

Run from repo root (`.\Sambhaash_AI`).

```powershell
python -m pip install -r .\Backend\requirements.txt
```

Make sure `Backend/env` exists and contains at least:
- `OPENAI_API_KEY`
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_PHONE_NUMBER`
- `TWILIO_WHATSAPP_FROM`

Start backend:

```powershell
uvicorn Backend.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 4) Quick local validation (before Twilio)

In a new terminal:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:8000/ready -UseBasicParsing
```

Expected:
- HTTP 200 for both
- `/ready` should show `twilio` and `openai` service flags

Check Twilio voice webhook response XML:

```powershell
Invoke-WebRequest -Method POST http://127.0.0.1:8000/api/webhook/twilio/voice -UseBasicParsing
```

Expected response body contains TwiML tags like `<Response>`, `<Say>`, `<Record>`.

---

## 5) ngrok setup (to receive Twilio webhooks)

Install ngrok, then expose your local backend:

```powershell
ngrok http 8000
```

Copy the HTTPS forwarding URL from ngrok, e.g.:
- `https://abcd-12-34-56-78.ngrok-free.app`

Optional but recommended: set this in `Backend/env`:
- `TWILIO_WEBHOOK_BASE_URL=https://abcd-12-34-56-78.ngrok-free.app`

Restart backend after env updates.

---

## 6) Twilio Voice testing (step-by-step)

1. Open Twilio Console → **Phone Numbers** → your active number.
2. Under **Voice Configuration**:
   - A call comes in → **Webhook**
   - URL: `https://<your-ngrok-url>/api/webhook/twilio/voice`
   - Method: `HTTP POST`
3. Save configuration.
4. Call your Twilio number from your phone.
5. Speak after the beep and wait for processing.
6. Inspect backend logs for:
   - inbound webhook log
   - transcription log (`Person 1 payload ready`)
   - detected language

If you do not get transcription:
- confirm ngrok URL is live
- verify Twilio number webhook method is POST
- verify OpenAI key in `Backend/env`
- verify Twilio account SID/token in `Backend/env`

---

## 7) Twilio WhatsApp sandbox testing (step-by-step)

You already joined sandbox (good ✅).

1. In Twilio Console → **Messaging** → **Try it out** → **WhatsApp Sandbox**.
2. Set **When a message comes in** webhook URL to:
   - `https://<your-ngrok-url>/api/webhook/twilio/whatsapp`
   - Method: `HTTP POST`
3. From your WhatsApp, send a test message to sandbox number (`+14155238886`).
4. You should receive auto XML-driven response:
   - “Thanks for messaging Sambhaash AI...”

---

## 8) API test commands

### Trigger outbound call

```powershell
$body = @{ phone_number = "+91XXXXXXXXXX" } | ConvertTo-Json
Invoke-RestMethod -Method POST -Uri http://127.0.0.1:8000/api/calls/outbound -ContentType "application/json" -Body $body
```

### Trigger WhatsApp send API

```powershell
$body = @{ phone_number = "+91XXXXXXXXXX" } | ConvertTo-Json
Invoke-RestMethod -Method POST -Uri http://127.0.0.1:8000/api/calls/whatsapp -ContentType "application/json" -Body $body
```

---

## 9) Known prototype constraints

- Current voice flow is recording-based, not real-time streaming.
- Person 2 handoff is currently logging payload (not yet queue/API integrated).
- TTS loopback to caller is minimal and can be expanded by Person 3 integration.

---

## 10) Security note (important)

If any credentials were ever committed to git history, rotate them immediately:
- Twilio auth token
- OpenAI API key
- Supabase keys
- Any other provider secrets

Keep secrets only in `Backend/env` (ignored by git).
