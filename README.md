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

To solve this, Sambhaash AI acts as an autonomous telephony orchestrator that seamlessly conducts outbound calls in over 10 regional Indian languages with human-like, sub-second latency, completely automating the initial engagement and qualification process. 

---

## Key Features

- **High-Fidelity Multilingual Speech Engine:** Full support for 10 major Indian languages using Sarvam BulBul V3 and Groq Whisper.
- **Dynamic RAG Knowledge Base:** Real-time semantic knowledge retrieval during live calls using Hugging Face embeddings and pgvector to handle complex client objections on the fly.
- **Intelligent Lead Routing:** Analyzes call sentiment and automatically routes "Hot" leads directly to human Relationship Managers (RMs).
- **WhatsApp Follow-up Agent:** Automatically engages "Warm" leads post-call via context-aware WhatsApp chats to nurture them toward conversion.
- **Unified Admin Dashboard:** A beautiful React-based command center to upload CSV leads, monitor real-time AI accuracy, and view call transcripts.

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
    Llama[Groq Llama 3 8B]
    Sarvam[Sarvam BulBul V3 TTS]

    Admin -->|Uploads Leads| ReactUI
    ReactUI -->|Stores Leads| Supabase
    
    Supabase -->|Fetches Pending Leads| FastAPI
    FastAPI -->|Initiates Call| Twilio
    Twilio <-->|Audio Stream| Customer
    
    Twilio -->|Audio Bytes| Whisper
    Whisper -->|Transcribed Text| LangGraph
    LangGraph <-->|Semantic Search| PgVector
    LangGraph <-->|Context & State| Llama
    Llama -->|Generated Text| Sarvam
    Sarvam -->|Synthesized Audio| Twilio
    
    LangGraph -->|Sentiment & Intent Scoring| RedisQueue
    RedisQueue -->|High Intent Hot| Agent
    RedisQueue -->|Warm Leads| WhatsApp
    RedisQueue -->|Call Logs| Supabase
```

### How It Works (The Lifecycle)

1. **Lead Ingestion & Queuing:** Administrators upload campaign lists via the React dashboard. Leads are securely stored in **Supabase**, and outreach jobs are asynchronously scheduled into a **Redis task queue** to prevent bottlenecks.
2. **Telephony & Real-Time STT:** When a call connects via **Twilio SIP**, the live bidirectional audio stream is captured. The user's speech is chunked and streamed to **Groq Whisper** for ultra-fast, sub-second Speech-to-Text (STT) transcription.
3. **Cognitive Processing & RAG:** The transcribed text enters our **LangGraph** orchestration pipeline. Here, the system queries a **pgvector** database (using Hugging Face embeddings) to fetch relevant knowledge base articles, ensuring the AI can handle complex, domain-specific objections accurately via **Llama 3 (8B)**.
4. **Synthesis (TTS) & Action:** The generated response text is instantly synthesized into high-fidelity, emotionally resonant regional audio using **Sarvam AI (BulBul V3)** and streamed back to the user.
5. **Intelligent Handoff:** Post-call, LangGraph evaluates the entire transcript's sentiment and intent. **"Hot"** leads instantly trigger a live handoff to a Relationship Manager (RM), while **"Warm"** leads are automatically nurtured via our context-aware **WhatsApp Follow-up Agent**.

---

## Tech Stack

### Frontend  
<img src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" /> <img src="https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white" /> <img src="https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white" />

### Backend  
<img src="https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi&logoColor=white" /> <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" /> <img src="https://img.shields.io/badge/Celery-37814A?style=for-the-badge&logo=celery&logoColor=white" /> <img src="https://img.shields.io/badge/LangGraph-232F3E?style=for-the-badge&logo=langchain&logoColor=white" />

### Database  
<img src="https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white" /> <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" /> <img src="https://img.shields.io/badge/pgvector-316192?style=for-the-badge&logo=postgresql&logoColor=white" /> <img src="https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white" />

### APIs & AI Models  
<img src="https://img.shields.io/badge/Groq-F55036?style=for-the-badge&logo=groq&logoColor=white" /> <img src="https://img.shields.io/badge/Meta_Llama_3-040D21?style=for-the-badge&logo=meta&logoColor=white" /> <img src="https://img.shields.io/badge/OpenAI_Whisper-412991?style=for-the-badge&logo=openai&logoColor=white" /> <img src="https://img.shields.io/badge/Sarvam.ai--BulBul_V3-FF5A5F?style=for-the-badge" /> <img src="https://img.shields.io/badge/Twilio-F22F46?style=for-the-badge&logo=twilio&logoColor=white" /> <img src="https://img.shields.io/badge/Hugging_Face-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black" />

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
- Python 3.9+ & pip
- Docker (for Redis)
- API Keys: Supabase, Groq, Hugging Face, Sarvam, Twilio, Ngrok

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
source venv/Scripts/activate # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env # Configure environment variables

# 3. Start Infrastructure & Workers
docker run -d --name sambhaash-redis -p 6379:6379 redis:alpine
python run_worker.py # Start async background worker

# 4. Start Backend API
python -m uvicorn main:app --reload
```

---

## Future Scope

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