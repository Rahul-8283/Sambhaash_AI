## Phase 2A: RAG Context Injection in Calls - Implementation Guide

### Overview
Phase 2A automatically retrieves relevant Knowledge Base (KB) articles during calls and injects them into the LLM prompt. This allows the AI to provide grounded, accurate responses based on your organization's documentation.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CALL FLOW WITH RAG                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  1. USER SPEAKS → Twilio Records → /api/webhook/recording  │
│     │                                                         │
│  2. TRANSCRIBE → WhisperService STT                         │
│     │                                                         │
│  3. DETECT LANGUAGE → LanguageDetector                      │
│     │                                                         │
│  4. [NEW] RETRIEVE KB CONTEXT                               │
│     ├─ KBContextInjectionService                            │
│     ├─ Embed user text (EmbedderService)                    │
│     ├─ Vector search (pgvector)                             │
│     ├─ Get top 3 relevant chunks                            │
│     └─ Format for prompt                                    │
│     │                                                         │
│  5. AUGMENTED LLM CALL                                      │
│     ├─ Orchestrator receives KB context                     │
│     ├─ Merges with RAG engine results                       │
│     ├─ Builds system + user prompts                         │
│     └─ Sends to LLM with context                            │
│     │                                                         │
│  6. GENERATE RESPONSE                                       │
│     ├─ LLM generates grounded response                      │
│     └─ AI can cite KB articles                              │
│     │                                                         │
│  7. LOG KB USAGE                                            │
│     └─ Store in call_sessions.kb_usage_log                  │
│     │                                                         │
│  8. CONVERT TO SPEECH                                       │
│     ├─ SarvamTTSService (text-to-speech)                    │
│     └─ Play to caller                                       │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### New Components

#### 1. KBContextInjectionService (`services/llm/kb_context_injection.py`)

**Purpose**: Retrieve and format KB context for calls

**Key Methods**:
- `retrieve_context_for_call()` - Query KB for relevant chunks
- `_format_context_for_prompt()` - Format chunks for LLM
- `_log_kb_usage()` - Track which KB articles were used
- `get_kb_analytics_for_call()` - Retrieve usage analytics

**Flow**:
```python
# In webhook_routes.py - recording_webhook()
kb_context = await kb_service.retrieve_context_for_call(
    call_session_id=session_id,
    lead_id=lead_id,
    user_text=transcript,           # User's message
    language=detected_lang,
    top_k=3,                          # Get top 3 chunks
    min_score=0.3                     # Minimum relevance
)

# Returns:
{
    "context_blocks": [               # Formatted chunks
        {
            "rank": 1,
            "chunk_id": "...",
            "doc_id": "...",
            "title": "Appendix A",
            "text": "...",
            "relevance_score": 0.85
        },
        ...
    ],
    "doc_ids_used": ["doc1", "doc2", "doc3"],
    "relevance_scores": [0.85, 0.78, 0.72],
    "total_tokens": 450,
    "formatted_context": "=== RELEVANT KB...",  # For injection
    "kb_available": True
}
```

#### 2. Updated CallSession Schema

**New Field**: `kb_usage_log` (JSON)

```sql
ALTER TABLE call_sessions ADD COLUMN kb_usage_log JSON DEFAULT '[]';
```

**Format**:
```json
[
  {
    "timestamp": "2026-05-05T10:30:00",
    "query": "How to use the product",
    "documents_used": ["doc_id_1", "doc_id_2"],
    "relevance_scores": [0.85, 0.78]
  },
  {
    "timestamp": "2026-05-05T10:35:00",
    "query": "What are the benefits?",
    "documents_used": ["doc_id_3"],
    "relevance_scores": [0.82]
  }
]
```

#### 3. Updated CallManager (`services/telephony/call_manager.py`)

**New Parameter**: `kb_context` in `process_turn()`

```python
async def process_turn(
    self,
    call_sid: str,
    user_text: str,
    language: str,
    kb_context: Optional[Dict[str, Any]] = None  # NEW
) -> Tuple[str, str]:
    """
    Now accepts KB context and passes it to Orchestrator
    """
    request_obj = OrchestrationRequest(
        lead_id=call_sid,
        user_text=user_text,
        language=language,
        session_id=call_sid,
        metadata={
            "kb_context": kb_context if kb_context else {},
            "kb_available": kb_context.get("kb_available", False) if kb_context else False
        }
    )
```

#### 4. Updated Orchestrator (`services/llm/orchestrator.py`)

**KB Context Merging** (new code):

```python
# After RAG engine retrieval
retrieved_context = self.rag_engine.retrieve(...)

# NEW: Merge KB Context if available
if request.metadata and request.metadata.get("kb_context"):
    kb_context = request.metadata.get("kb_context")
    kb_formatted = kb_context.get("formatted_context", "")
    
    if kb_formatted:
        # Prepend KB context for high priority
        retrieved_context = [kb_formatted] + list(retrieved_context or [])
        logger.info(f"[PHASE2A] KB Context injected ({len(kb_context['context_blocks'])} chunks)")
```

The KB context is then passed to `prompt_builder.build_bundle()` which includes it in the system/user prompts sent to the LLM.

### Analytics Endpoints (Phase 2A)

New routes in `/admin/kb/analytics`:

#### 1. Get Call KB Analytics
```
GET /admin/kb/analytics/call/{session_id}
```

**Response**:
```json
{
  "call_session_id": "uuid",
  "total_queries": 3,
  "total_documents_used": 5,
  "unique_documents": 3,
  "avg_relevance_score": 0.82,
  "documents_list": ["doc1", "doc2", "doc3"],
  "usage_log": [
    {
      "timestamp": "2026-05-05T10:30:00",
      "query": "How to use?",
      "documents_used": ["doc1", "doc2"],
      "relevance_scores": [0.85, 0.78]
    }
  ]
}
```

#### 2. Get KB Effectiveness Metrics
```
GET /admin/kb/analytics/effectiveness?limit_days=7
```

**Response**:
```json
{
  "total_calls_analyzed": 42,
  "calls_with_kb_usage": 38,
  "avg_documents_per_call": 2.8,
  "avg_relevance_score": 0.81,
  "most_used_documents": [
    {
      "document_name": "Appendix A",
      "usage_count": 45,
      "avg_relevance": 0.82
    }
  ],
  "kb_coverage_percentage": 90.5
}
```

#### 3. Get Document Impact
```
GET /admin/kb/analytics/document-impact/{doc_id}
```

**Response**:
```json
{
  "document_id": "uuid",
  "times_retrieved": 24,
  "avg_relevance_score": 0.81,
  "calls_using_document": 24,
  "leads_converted_with_this_doc": 6,
  "conversion_rate": 0.25,
  "top_queries": [
    {"query": "How to use?", "count": 5}
  ],
  "impact_score": 0.78
}
```

### Testing Phase 2A

1. **Upload a KB Document**
   ```bash
   POST /admin/kb/upload
   Form Data:
   - file: Appendix_A.pdf
   - doc_type: appendix_a
   - language: hi
   ```

2. **Initiate a Call** (backend will automatically find NEW leads)
   - Call initiator runs every 30 seconds
   - Calls NEW leads

3. **Monitor KB Usage During Call**
   - Call webhook receives recording
   - KBContextInjectionService retrieves context
   - Orchestrator merges KB into prompt
   - AI responds with grounded knowledge

4. **Check Analytics**
   ```bash
   GET /admin/kb/analytics/call/{session_id}
   ```
   - View which KB articles were used
   - See relevance scores
   - Check usage timeline

### Configuration

**From .env** (already set):
```
SUPABASE_URL=https://cyzauakzjwwivbzkzxnx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_BUCKET_NAME=knowledge-base-documents
DATABASE_URL=postgresql+asyncpg://...
```

**Embedding Model**:
- Model: all-MiniLM-L6-v2
- Dimensions: 384
- No API key needed (local)
- Batch processing: Yes

**Search Parameters**:
- top_k: 3 (retrieve top 3 chunks)
- min_score: 0.3 (minimum relevance threshold)
- Strategy: Semantic similarity via pgvector

### Performance Optimization

1. **Lazy Loading**: Services initialized on first use
2. **Batch Embeddings**: Multiple texts embedded in one call
3. **Caching**: Embedder model cached after first load
4. **Async**: All DB calls non-blocking
5. **pgvector**: GPU-accelerated similarity search (if available)

### Data Model

```
Call Flow:
Lead → Call Session → Conversation Turns → KB Usage Log
                          ↓
                    Webhook Recording
                          ↓
                    Transcription (Whisper)
                          ↓
                    KB Retrieval (Phase 2A)
                          ↓
                    LLM with Context
                          ↓
                    Response + TTS
                          ↓
                    KB Usage Logged
```

### Error Handling

- If KB service fails: Falls back to RAG engine only
- If embedder fails: Uses RAG engine results only
- If vector search fails: Gracefully skips KB context
- All errors logged with [KB_CTX] prefix

### Next Phases

- **Phase 2B**: Call transcription & recording storage
- **Phase 2C**: Conversation history analytics
- **Phase 2D**: Intent detection from call transcriptions
- **Phase 3**: Auto-scoring from call context

### Monitoring

Log all KB context operations:
```
[KB_CTX] Retrieving context for call {session_id}
[KB_CTX] Retrieved {N} KB chunks
[KB_CTX] Formatted context ({N} chunks, ~{TOKENS} tokens)
[KB_CTX] Logged KB usage for session {session_id}
[PHASE2A] KB Context injected ({N} chunks)
```

### Database Migration Required

Run this SQL to add kb_usage_log if migrating existing database:

```sql
ALTER TABLE call_sessions 
ADD COLUMN IF NOT EXISTS kb_usage_log JSON NOT NULL DEFAULT '[]';
```

### Summary

Phase 2A automatically:
1. Detects what the user is asking about
2. Retrieves relevant KB articles
3. Injects them into the LLM prompt
4. Enables grounded AI responses
5. Tracks KB usage for analytics

This dramatically improves AI response quality by grounding answers in your actual documentation.
