# Call flow

How a lead goes from `NEW` to a scored, routed outcome. Code references are to
the current implementation; [`../../CODE_AUDIT.md`](../../CODE_AUDIT.md) lists
what is still missing.

## 1. Dialing — `worker/call_initiator.py`

`run_worker.py` runs two loops in one process: the dialer and the Redis job
worker. Every 30 s the dialer:

1. selects leads with status `NEW`;
2. creates a `call_sessions` row;
3. asks Twilio for an outbound call whose `Url` is
   `{base}/api/webhook/twilio/voice?session_id=…&lead_id=…`;
4. sets the lead to `CONTACTED`.

A permanent failure (invalid number) marks the lead `REJECTED`; a transient one
leaves it `NEW` for the next cycle.

## 2. The turn loop — `api/routes/webhook_routes.py`

```
voice webhook ── greeting in the lead's saved language (Sarvam <Play>; English <Say> if TTS fails) + <Record action=/recording?session_id&lead_id>
   │
recording webhook (one per caller utterance)
   ├─ read stored turns (language so far, history)
   ├─ Whisper transcribes (language hint from turn 2)      ┐ blocking calls run
   ├─ language detected; short replies keep call language  │ in threads
   ├─ KB lookup (local embeddings + cosine similarity)     ┘
   ├─ LangGraph: intent → rag | objection | pitch → outcome
   ├─ save the turn  ∥  TTS (reply split in two, parallel)
   └─ <Play audio> + <Record> again   — or score and <Hangup>
```

The call so far is rebuilt from `call_sessions.conversation_history` on every
turn (`orchestration/history.py`); the graph has no checkpointer. The next-turn
`<Record>` URL carries `session_id` and `lead_id`, so the call survives a server
restart. Audio is held in an in-process dict and served from
`/api/webhook/twilio/audio/{call_sid}`, so it only works while the same API
process handles the call.

## 3. Outcome

`orchestration/outcome.py` reads the caller's words (whole words; "not
interested" is a refusal): a clear yes/interested → HOT, a clear no/stop → COLD,
newest signal wins. The call ends on a clear signal or at `MAX_TURNS_PER_SESSION`.

`_score_and_assign_lead` then runs `ScoringEngine` over the stored conversation
(intent, engagement, sentiment, real call duration). A clear HOT/COLD keyword
outcome overrides the engine; otherwise the engine's classification is used
(composite ≥ 0.75 HOT, ≥ 0.50 WARM, else COLD).

| Class | Lead status | Action |
|---|---|---|
| HOT | `INTERESTED` | assigned to `DEFAULT_RM_NAME` (no live transfer, no RM notification) |
| WARM | `INTERESTED` | `send_whatsapp` job (`warm_follow_up`) in the lead's language |
| COLD | `FOLLOW_UP` | none; not re-dialled |

A `send_summary` job is queued for every scored call.

Twilio's `status` webhook handles the calls that do not reach scoring:
`failed`, `busy`, `no-answer`, `canceled` and voicemail park the lead as
`FOLLOW_UP`; a call that was answered but hung up before the caller said
anything is also parked (there is nothing to score); a caller who spoke and then
hung up is scored from what they said.

## 4. Data written

| Table / column | Written by |
|---|---|
| `call_sessions.conversation_history` | every turn: `{user, ai, language, timestamp}` |
| `call_sessions.kb_usage_log` | KB lookups (background) |
| `call_sessions.duration_seconds`, `language_detected` | scoring, language detection |
| `lead_scores` | scoring |
| `leads.status`, `leads.language` | scoring, language detection |
| `rm_assignments` | HOT |
| `objections_log` | objection turns (see below) |

`objections_log` — one row per objection turn (type price / trust / timing /
  not_interested / other), marked resolved if the call ends HOT.

## Latency budget

Per turn: Whisper + LLM (~0.2–0.5 s) + TTS (~1.4 s for a two-sentence reply) +
Twilio's fetch. Replies are capped at 160 tokens and two sentences because TTS
time grows with length. Sarvam `bulbul:v3` is the floor at roughly 1.5 s per
request.
