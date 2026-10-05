"""
Conversation memory for a call

Each call's turns are stored in call_sessions.conversation_history as
{"user": ..., "ai": ..., "language": ..., "timestamp": ...}. On every turn the
graph is given the stored conversation rebuilt as LangChain messages, so the
model remembers what was said earlier in the same call.
"""

import json
from typing import List

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

# Keep the prompt bounded on long calls; the most recent turns matter most
MAX_HISTORY_TURNS = 20


def history_to_messages(history) -> List[BaseMessage]:
    """Convert stored turns (list or JSON text) into alternating Human/AI messages."""
    if isinstance(history, str):
        try:
            history = json.loads(history)
        except ValueError:
            return []
    if not isinstance(history, list):
        return []

    messages: List[BaseMessage] = []
    for turn in history[-MAX_HISTORY_TURNS:]:
        if not isinstance(turn, dict):
            continue
        if turn.get("user"):
            messages.append(HumanMessage(content=str(turn["user"])))
        if turn.get("ai"):
            messages.append(AIMessage(content=str(turn["ai"])))
    return messages
