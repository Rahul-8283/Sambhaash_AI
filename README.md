<div align="center">
  <img src="Frontend/public/logo.png" alt="Sambhaash AI Logo" width="80" />
  <h1>Sambhaash AI</h1>
  <p><strong>A Premium Multilingual Voice AI Platform for Automated Lead Generation</strong></p>
</div>

---

## Awards & Achievements

**Sambhaash AI is a winning project from the Namespace Hackathon!**
- 🥉 **3rd Place Globally (Sarvam AI Track):** Awarded $200 in Sarvam AI credits for building a high-fidelity conversational agent using BulBul V3.
- 🌍 **Top 50 Globally (Overall):** Recognized as a top 50 project worldwide, winning a $20 cash prize for excellence in the Work, Finance & Digital Economy theme.

---

## Overview

**Sambhaash AI** is an enterprise-grade multilingual voice AI platform designed to automate lead generation and overcome linguistic barriers in business outreach. Traditional telecalling operations suffer from massive manual overhead and high drop-off rates when agents cannot converse in a lead’s native tongue. 

To solve this, Sambhaash AI acts as an autonomous telephony orchestrator that seamlessly conducts outbound calls in 11 Indian languages, answering each turn in a couple of seconds, completely automating the initial engagement and qualification process. 

---

## Key Features

- **Multilingual Speech Engine:** English, Hindi and nine regional languages (Marathi, Bengali, Gujarati, Punjabi, Odia, Tamil, Telugu, Kannada, Malayalam) using Sarvam BulBul V3 for speech and Groq Whisper for transcription. The call opens with a greeting in the lead's saved language, and the language spoken on the call is then detected, remembered and used for the reply and the follow-up.
- **Dynamic RAG Knowledge Base:** Real-time semantic knowledge retrieval during live calls using local sentence-transformer embeddings and pgvector to handle complex client objections on the fly.
- **Lead Scoring & Routing:** Scores each call on intent, engagement and sentiment and classifies it HOT / WARM / COLD. HOT leads go to the least-loaded Relationship Manager in the configured roster, who is notified on WhatsApp (with an optional live transfer of the call); COLD leads are not re-dialled, and a spoken do-not-contact request permanently stops all calls to that lead.
- **WhatsApp Follow-up Agent:** Sends WARM leads a Partner Program follow-up in their own language and answers their replies with an LLM.
- **Unified Admin Dashboard:** A React command center to upload CSV leads, manage the knowledge base, review each call's transcript, score and summary, and work the RM queue.

---

## Architecture

The overall functional flow of Sambhaash AI covers the entire lifecycle—from the administrator uploading lead contacts to telephony engagement, RAG vector lookup, lead scoring, and intelligent handoffs.

<p align="center">
  <img src="Images/flowchart.png" alt="Sambhaash AI Architecture Diagram" width="800" />
</p>

```mermaid
graph TD
    Admin([Admin])
    Customer([Customer])
    Agent([RM Agent])
    
    ReactUI[React Admin Dashboard]
    Supabase[(Supabase DB)]
    PgVector[(PgVector RAG DB)]
    RedisQueue[[Redis Task Queue]]
    WhatsApp[WhatsApp API]
    Twilio[Twilio SIP/Telephony]
    
    FastAPI{FastAPI Backend}
    LangGraph((LangGraph Orchestrator))
    Whisper[Groq Whisper STT]
    LLM[Groq Qwen 3.8 27B]
    Sarvam[Sarvam BulBul V3 TTS]

    Admin -->|Uploads Leads| ReactUI
    ReactUI -->|Stores Leads| Supabase
    
    Supabase -->|Fetches Pending Leads| FastAPI
    FastAPI -->|Initiates Call| Twilio
    Twilio <-->|Audio Stream| Customer
    
    Twilio -->|Audio Bytes| Whisper
    Whisper -->|Transcribed Text| LangGraph
    LangGraph <-->|Semantic Search| PgVector
    LangGraph <-->|Context & State| LLM
    LLM -->|Generated Text| Sarvam
    Sarvam -->|Synthesized Audio| Twilio
    
    LangGraph -->|Sentiment & Intent Scoring| RedisQueue
    RedisQueue -->|High Intent Hot| Agent
    RedisQueue -->|Warm Leads| WhatsApp
    RedisQueue -->|Call Logs| Supabase
```

### How It Works (The Lifecycle)

1. **Lead Ingestion:** Administrators upload campaign lists via the React dashboard. Numbers are normalized to E.164 and leads are stored in **Supabase** with status `NEW`. New leads are only dialled between 09:00 and 21:00 IST.
2. **Dialing:** A background worker picks up `NEW` leads and has **Twilio** place the call. Each caller utterance is recorded and posted to the backend, which answers with the next spoken reply (a record-and-respond loop, not a live audio stream).
3. **Transcription & Retrieval:** **Groq Whisper** transcribes the recording and the language is detected. The utterance is embedded locally and matched against the knowledge base to pull relevant chunks.
4. **Reasoning & Speech:** A **LangGraph** graph, given the call so far, picks a pitch / objection / knowledge-answer path and writes a short reply with a **Groq**-hosted LLM, which **Sarvam BulBul V3** synthesizes in the caller's language. The opening greeting is spoken in the lead's saved language.
5. **Scoring & Follow-up:** When the caller gives a clear yes or no, or the call reaches its turn limit, the whole conversation is scored. **HOT** leads are assigned to the least-loaded Relationship Manager (who gets a WhatsApp notification, and the call can be transferred live), **WARM** leads receive a WhatsApp follow-up in their language, and **COLD** leads are parked. Leads that never answered can optionally be retried by the nurture schedule. A call summary is generated for every scored call.

---

## Tech Stack

### Frontend  
<img src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" /> <img src="https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white" /> <img src="https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white" />

### Backend  
<img src="https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi&logoColor=white" /> <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" />  <img src="https://img.shields.io/badge/LangGraph-232F3E?style=for-the-badge&logo=langchain&logoColor=white" />

### Database  
<img src="https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white" /> <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" /> <img src="https://img.shields.io/badge/pgvector-316192?style=for-the-badge&logo=postgresql&logoColor=white" /> <img src="https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white" />

### APIs & AI Models  
<img src="https://img.shields.io/badge/Groq-F55036?style=for-the-badge&logo=groq&logoColor=white" /> <img src="https://img.shields.io/badge/OpenAI_Whisper-412991?style=for-the-badge&logo=openai&logoColor=white" /> <img src="https://img.shields.io/badge/Sarvam.ai--BulBul_V3-FF5A5F?style=for-the-badge" /> <img src="https://img.shields.io/badge/Twilio-F22F46?style=for-the-badge&logo=twilio&logoColor=white" />

### Hosting & DevOps  
<img src="https://img.shields.io/badge/Render-46E3B7?style=for-the-badge&logo=render&logoColor=white" /> <img src="https://img.shields.io/badge/Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white" /> <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" />

---

## Platform Previews

<div align="center">
  <img src="Images/sam1.webp" alt="Dashboard Preview 1" width="800" />
  <br /><br />
  <img src="Images/sam11.webp" alt="Dashboard Preview 2" width="800" />
  <br /><br />
  <img src="Images/sam2.webp" alt="Dashboard Preview 3" width="800" />
  <br /><br />
  <img src="Images/sam3.webp" alt="Dashboard Preview 4" width="800" />
</div>

---

## Local Setup

### Requirements:
- Node.js & npm
- Python 3.11 (matches the Dockerfile) & pip
- Docker (for Redis)
- API Keys: Supabase, Groq, Sarvam, Twilio, Ngrok

See [`Backend/README.md`](Backend/README.md) for configuration, safety notes and troubleshooting, and [`CODE_AUDIT.md`](CODE_AUDIT.md) for what is and is not implemented.

### Setup Instructions:
```bash
# 1. Frontend Setup
cd Frontend
cp .env.example .env # Configure environment variables
npm install
npm run dev

# 2. Backend Setup
cd ../Backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env # Configure environment variables
python scripts/migrate.py --apply # Apply the pending SQL migrations (conversion notes, lead notes)

# 3. Start Infrastructure & Workers
docker run -d --name sambhaash-redis -p 6379:6379 redis:alpine
python run_worker.py # Start dialer + job worker (it calls every NEW lead: see Backend/README.md)

# 4. Start Backend API (start this before the worker)
# For local calls set ENABLE_NGROK=true with MODE=development and NGROK_AUTH_TOKEN; the tunnel is off by default.
# Don't edit backend files during a live call while using --reload: the restart drops the call.
python -m uvicorn main:app --reload

# 5. Run the tests (no external services needed)
pytest
```

---

## Future Scope

- **Richer RM tooling:** a per-RM dashboard and working hours / availability-aware assignment on top of the current roster allocation.
- **More integrations:** Native integrations with standard CRM systems (Salesforce, HubSpot) to automatically update lead statuses and log call transcripts.
- **Security enhancements:** Enhanced access controls and PII redaction during LLM processing.
- **Localization / broader accessibility:** Expanding to international language models for global outreach and implementing custom voice branding/cloning.

---

## Contributors (Team TetraFourge)

- **Rahul L S** ([GitHub](https://github.com/Rahul-8283) | [LinkedIn](https://www.linkedin.com/in/rahul-ls))  
- **Kesav** ([GitHub](https://github.com/kesavvvvvv) | [LinkedIn](https://www.linkedin.com/in/kesav-satya-sai-nimmagadda-673164317))
- **Kabilan K** ([GitHub](https://github.com/KKabilan07) | [LinkedIn](https://www.linkedin.com/in/kabilank07/))
- **Prajwal Priyadarshan G** ([GitHub](https://github.com/prajwal-priyadarshan) | [LinkedIn](https://www.linkedin.com/in/prajwal-priyadarshan/))
- **Kishore B** ([GitHub](https://github.com/KishoreB25) | [LinkedIn](https://www.linkedin.com/in/kishore-b-245a66343))

---

<div align="center">
  <p>Built by Team TetraFourge for the Namespace Hackathon (Sarvam AI Track)</p>
</div>
