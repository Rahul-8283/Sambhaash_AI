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
