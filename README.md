<img width="4320" height="1440" alt="hh26 main poster 2 with sponsors 3x1 (4320 x 1440 px) (2)" src="https://github.com/user-attachments/assets/c698b2cd-da84-4cb0-9276-125c6a7244aa" />

# <img src="Frontend/public/logo.png" alt="Sambhaash AI Logo" width="35" align="center" /> Sambhaash AI

> A Premium Multilingual Voice AI Platform built for the Namespace Hackathon.

---

## 📌 Problem & Domain

Traditional telecalling and lead qualification processes in India face severe bottlenecks: immense manual overhead, high drop-off rates due to language barriers, and a lack of scalable, intelligent 24/7 engagement.

**Themes Selected (at least one):**
- [x] Human Experience & Productivity  
- [ ] Climate & Sustainability Systems  
- [ ] HealthTech & Bio Platforms  
- [ ] Learning & Knowledge Systems  
- [x] Work, Finance & Digital Economy  
- [ ] Infrastructure, Mobility & Smart Systems  
- [ ] Trust, Identity & Security  
- [ ] Media, Social & Interactive Platforms  
- [ ] Public Systems, Governance and Civic Tech  
- [ ] Developer Tools & Software Infrastructure  

---

## 🎯 Objective

**Target Users:** Businesses, sales teams, and organizations operating in India that require scalable, localized lead generation and engagement.
**The Pain Point:** Human telecalling has immense manual overhead, suffers from language barriers across India's diverse linguistic landscape, and is limited by working hours.
**The Value Provided:** Sambhaash AI is a premium, state-of-the-art multilingual voice and text conversational AI platform. Powered by an intelligent LLM brain, it interacts with leads via phone calls and WhatsApp, answers context-specific questions from an indexed Knowledge Base, scores leads dynamically, and assigns high-intent clients directly to dedicated Relationship Managers.

---

## 🧠 Team & Approach

### Team Name:  
`TetraFourge`

### Team Members:  
- **Rahul L S** ([GitHub](https://github.com/Rahul-8283) | [LinkedIn](https://www.linkedin.com/in/rahul-ls))  
- **Kishore B** ([GitHub](https://github.com/KishoreB25) | [LinkedIn](https://www.linkedin.com/in/kishore-b-245a66343))
- **Prajwal Priyadarshan G** ([GitHub](https://github.com/prajwal-priyadarshan) | [LinkedIn](https://www.linkedin.com/in/prajwal-priyadarshan/))
- **Kabilan K** ([GitHub](https://github.com/KKabilan07) | [LinkedIn](https://www.linkedin.com/in/kabilank07/))

### Your Approach:
- **Why you chose this problem:** India's linguistic diversity makes unified communication incredibly difficult. Overcoming language barriers in business outreach can multiply engagement rates tremendously.
- **Key challenges you addressed:** Orchestrating sub-second latency for multilingual voice AI interactions (Speech-to-Text -> LLM generation -> Text-to-Speech) to make phone calls feel natural.
- **Breakthroughs:** Utilizing Sarvam's BulBul V3 for hyper-realistic Indian language synthesis and creating a robust RAG vector lookup during live call sessions to handle dynamic objections.

---

## 🛠️ Tech Stack

### Core Technologies Used:

**Frontend**  
<img src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" /> <img src="https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white" /> <img src="https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white" />

**Backend**  
<img src="https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi&logoColor=white" /> <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" /> <img src="https://img.shields.io/badge/Celery-37814A?style=for-the-badge&logo=celery&logoColor=white" /> <img src="https://img.shields.io/badge/LangGraph-232F3E?style=for-the-badge&logo=langchain&logoColor=white" />

**Database**  
<img src="https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white" /> <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" /> <img src="https://img.shields.io/badge/pgvector-316192?style=for-the-badge&logo=postgresql&logoColor=white" /> <img src="https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white" />

**APIs & AI Models**  
<img src="https://img.shields.io/badge/Groq-F55036?style=for-the-badge&logo=groq&logoColor=white" /> <img src="https://img.shields.io/badge/Meta_Llama_3-040D21?style=for-the-badge&logo=meta&logoColor=white" /> <img src="https://img.shields.io/badge/OpenAI_Whisper-412991?style=for-the-badge&logo=openai&logoColor=white" /> <img src="https://img.shields.io/badge/Sarvam.ai--BulBul_V3-FF5A5F?style=for-the-badge" /> <img src="https://img.shields.io/badge/Twilio-F22F46?style=for-the-badge&logo=twilio&logoColor=white" /> <img src="https://img.shields.io/badge/Hugging_Face-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black" />

**Hosting & DevOps**  
<img src="https://img.shields.io/badge/Render-46E3B7?style=for-the-badge&logo=render&logoColor=white" /> <img src="https://img.shields.io/badge/Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white" /> <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" />

### Additional Technologies Used (Optional):
- [x] AI / ML  
- [ ] Web3 / Blockchain  
- [ ] Cyber Security 
- [ ] Cloud  

---

## 🏆 Sponsored Track (Optional)

- [ ] **Expo Track** – Built using Expo  
- [ ] **Neo4j Track** – Uses AuraDB as primary database  
- [ ] **Base44 Track** – Prototype/Final Product built using Base44  
- [x] **Sarvam AI Track** – Build AI Applications with Sarvam AI

**Note on partner technology usage:**
> *We explicitly designed the core of Sambhaash's voice orchestration to run on Sarvam's BulBul V3 API. This allows the AI to synthesize highly accurate, natural-sounding audio in 10 regional Indian languages with sub-second latency.*

---

## ✨ Key Features

- ✅ **Unified Lead Administration Dashboard:** Dynamic lead insertion (CSV or manual) and advanced filtering by Call Status, Language, and Lead Score.
- ✅ **High-Fidelity Multilingual Speech Engine:** Full support for 10 major Indian languages using Sarvam BulBul V3 and Groq Whisper.
- ✅ **Dynamic RAG Vector Database:** Real-time semantic knowledge retrieval during live calls using Hugging Face embeddings and pgvector to handle client objections.
- ✅ **Intelligent Lead Segregation:** Automatically routes HOT leads to specific RM agents and engages WARM leads with automated, personalized WhatsApp follow-ups.
- ✅ **Premium Real-Time Analytics:** Monitoring of AI response accuracy, call stats, and top knowledge asset utility.

---

## 📐 Architecture

The overall functional flow of Sambhaash AI covers the entire lifecycle—from the administrator uploading lead contacts to telephony engagement, RAG vector lookup, lead scoring, automated WhatsApp conversational follow-ups, and Relationship Manager allocation.

![Sambhaash AI Project Flowchart](Images/flowchart.png)

---

## 📽️ Demo & Deliverables

- **Demo Video Link (Mandatory):**  
  [![Demo Video](https://img.shields.io/badge/Watch_Demo_Video-FF0000?style=for-the-badge&logo=youtube&logoColor=white)](https://canva.link/6810z8dp5k71r8l)
- **Deployment Links (Recommended):**  
  - **Frontend Live App:** [https://sambhaash-ai.vercel.app](https://sambhaash-ai.vercel.app)
  - **Backend API Server:** [https://sambhaash-api.onrender.com](https://sambhaash-api.onrender.com)
- **Pitch Deck / PPT (Optional):**  
  [![Pitch Deck](https://img.shields.io/badge/View_Pitch_Deck-00C4CC?style=for-the-badge&logo=canva&logoColor=white)](https://canva.link/6810z8dp5k71r8l)

---

## ✅ Tasks & Bonus Checklist

- [ ] All team members completed the mandatory social task  
- [ ] Bonus Task 1 – Badge sharing  
- [ ] Bonus Task 2 – Blog/article  

---

## 🧪 How to Run the Project

### Requirements:
- Node.js & npm
- Python 3.9+ & pip
- Docker (for Redis)
- API Keys: Supabase, Groq, Hugging Face, Sarvam, Twilio, Ngrok

### Local Setup:
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

## 🧬 Future Scope

- 📈 **More integrations:** Native integrations with standard CRM systems (Salesforce, HubSpot).
- 🛡️ **Security enhancements:** Enhanced access controls and PII redaction during LLM processing.
- 🌐 **Localization / broader accessibility:** Expanding to international language models for global outreach.

---

## 📎 Resources / Credits

- **Sarvam AI** for Text-to-Speech API
- **Groq** for high-speed Llama 3 LLM and Whisper transcription
- **Twilio** for Telephony and WhatsApp API
- **Supabase** for Backend Database and pgvector

---

## 🏁 Final Words

Building a sub-second latency multilingual conversational AI involved numerous architectural challenges, from streaming audio bytes smoothly to refining RAG lookup latency. It was an incredible journey blending speech recognition, dynamic context retrieval, and state-of-the-art TTS into a single cohesive platform.

---