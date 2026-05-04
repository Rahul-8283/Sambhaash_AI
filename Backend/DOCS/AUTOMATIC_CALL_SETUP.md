# 🚀 Automatic AI Call Integration - Setup Guide

## What I Just Implemented

### 1. **Call Initiator Scheduler** (`worker/call_initiator.py`)
- ✅ Finds NEW leads every 30 seconds
- ✅ Creates call session in database
- ✅ Initiates outbound Twilio call
- ✅ Pre-registers session in webhook cache
- ✅ Updates lead status to CONTACTED

### 2. **Enhanced Webhook** (`api/routes/webhook_routes.py`)
- ✅ Stores conversation history to database
- ✅ Saves each turn (user + AI response + language)
- ✅ Auto-scores leads after call
- ✅ Auto-assigns to RM if HOT (score ≥ 0.75)
- ✅ Schedules WhatsApp if WARM (0.50-0.75)
- ✅ Ends call after 50 turns max

### 3. **Updated Worker Runner** (`run_worker.py`)
- ✅ Runs Call Initiator + Job Processor together
- ✅ Call Initiator: Finds leads every 30s → calls them
- ✅ Job Processor: Handles async jobs (WhatsApp, scoring)

---

## 🎯 Complete Automatic Flow

```
1. Backend startup
   ↓
2. Worker starts
   ├─ Call Initiator: Looks for NEW leads every 30s
   └─ Job Processor: Processes async jobs from Redis queue
   ↓
3. NEW Lead Found (from API)
   ├─ lead_id: uuid
   ├─ phone: +919080427949
   ├─ status: NEW
   ├─ language: hi
   ↓
4. Call Initiator Picks It Up
   ├─ Creates call_session in database
   ├─ Pre-registers session in webhook cache
   ├─ Initiates Twilio call: create_outbound_call(+919080427949)
   ├─ Updates lead status: NEW → CONTACTED
   ↓
5. Customer Answers
   ├─ /api/webhook/twilio/voice triggered
   ├─ AI greets: "Hello, welcome to Sambhaash AI"
   ├─ Records speech
   ↓
6. Customer Speaks (Turn 1)
   ├─ /api/webhook/twilio/recording triggered
   ├─ STT: Whisper transcribes speech
   ├─ LLM: Orchestrator processes intent + objections
   ├─ TTS: Sarvam generates AI response in same language
   ├─ SAVES to database: Turn 1 history
   ├─ AI responds to customer
   ├─ Records next speech
   ↓
7. Repeat Turns 2-50
   ├─ Each turn saved to database
   ├─ Conversation history builds
   ↓
8. Max Turns Reached (50)
   ├─ Auto-scores lead:
   │  ├─ Interest: extracted from conversation
   │  ├─ Engagement: how responsive customer was
   │  ├─ Sentiment: positive/negative tone
   │  ├─ Composite: (I+E+S)/3
   ├─ Classification:
   │  ├─ HOT (≥0.75): Auto-assign to RM "Auto"
   │  ├─ WARM (0.50-0.74): Queue WhatsApp follow-up
   │  ├─ COLD (<0.50): Keep as NEW, retry later
   ├─ Updates lead status: CONTACTED → INTERESTED/REJECTED
   ├─ Call ends gracefully
   ↓
9. If HOT Lead
   ├─ /api/rm/queue shows lead for RM
   ├─ RM calls/messages customer
   ├─ RM marks as converted: /api/rm/{rm_name}/{lead_id}/complete
   ├─ Lead stats updated on leaderboard
   ↓
10. If WARM Lead
    ├─ WhatsApp job queued in Redis
    ├─ Job Worker sends WhatsApp message
    ├─ Customer gets follow-up
```

---

## 🔧 How to Use

### **Terminal 1: Start Backend API**
```bash
cd Backend
python -m uvicorn main:app --reload --port 8000
```

### **Terminal 2: Start Background Worker**
```bash
cd Backend
python run_worker.py
```

This will print:
```
========================================================================
🚀 Sambhaash AI Background Worker (Call Initiator + Job Processor)
========================================================================
🚀 Call Initiator Scheduler started (poll_interval=30s)
🚀 Worker started for SEND_WHATSAPP
🚀 Worker started for ASSIGN_RM
... (job workers start)
```

### **Terminal 3: Create a Lead**
```bash
curl -X POST http://127.0.0.1:8000/api/leads \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+919080427949",
    "name": "Rahul",
    "email": "rahul@example.com",
    "language": "hi"
  }'

# Response:
{
  "id": "3bcf0f8-1cbe-4252-b8ca-a4168f63b841",
  "phone": "+919080427949",
  "name": "Rahul",
  "status": "NEW",
  ...
}
```

### **Automatic!**
**Within 30 seconds, your phone will ring!** 📞

Logs in Terminal 2:
```
Found 1 NEW leads to call
Created call session: 8d3c8f5e-1234-5678-90ab-cdef12345678
✅ Call initiated for Rahul (+919080427949)
   Call SID: CA123456789abcdef123456789
   Session ID: 8d3c8f5e-1234-5678-90ab-cdef12345678
🔥 HOT lead assigned to RM: Auto
```

---

## 📊 Monitor Progress

### **Check Lead Queue (for RM)**
```bash
curl http://127.0.0.1:8000/api/rm/Auto/queue
```

### **Check Lead Scores**
```bash
curl "http://127.0.0.1:8000/api/leads"
```

### **Check RM Dashboard**
```bash
curl http://127.0.0.1:8000/api/rm/Auto/dashboard
```

### **Check Leaderboard**
```bash
curl http://127.0.0.1:8000/api/rm/leaderboard
```

---

## 🎯 What Happens After Call Ends

| Score | Classification | Action |
|-------|---|---|
| ≥ 0.75 | HOT 🔥 | Auto-assign to RM immediately |
| 0.50-0.74 | WARM 🟡 | Queue WhatsApp follow-up message |
| < 0.50 | COLD ❄️ | Remains NEW, retry call later |

---

## 📝 Database Logging

Everything is logged:

**leads table:**
- ✅ Phone, name, email, language
- ✅ Status: NEW → CONTACTED → INTERESTED/REJECTED
- ✅ Created/updated timestamps

**call_sessions table:**
- ✅ Lead ID, language detected
- ✅ Conversation history (array of {user, ai, language, timestamp})
- ✅ Duration, classification

**lead_scores table:**
- ✅ Interest, engagement, sentiment scores
- ✅ Composite score & classification
- ✅ Timestamp

**rm_assignments table:**
- ✅ Lead assigned to RM
- ✅ Assignment timestamp
- ✅ Conversion status

**objections_log table:**
- ✅ Objections detected during call
- ✅ Resolution status

---

## ✅ Checklist Before Running

- [ ] Twilio Account SID in .env ✓
- [ ] Twilio Auth Token in .env ✓
- [ ] Twilio Phone Number in .env ✓
- [ ] OpenAI API Key in .env ✓
- [ ] Sarvam API Key in .env ✓
- [ ] PostgreSQL/Supabase URL in .env ✓
- [ ] Redis running locally or configured ✓
- [ ] Database initialized (schema created) ✓

---

## 🚀 You're All Set!

The system will now:
1. Automatically find NEW leads
2. Call them with AI agent
3. Record conversations
4. Score leads
5. Assign to RMs or schedule follow-ups

**All automatic!** No manual intervention needed! 🎉
