from typing import Dict, Any
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from orchestration.state import AgentState, llm
from orchestration.outcome import classify_outcome
from utils.language import reply_language_instruction
import re

# Shared by every reply node. This is a live phone call: replies are spoken aloud,
# so they must be short (also the biggest lever on TTS time and silence on the line).
PERSONA = (
    "You are Sambhaash AI, a friendly phone sales agent for the Rupeezy Partner Program. "
    "Rupeezy is an Indian stock broking and investment platform; partners earn commissions "
    "by referring clients. You are speaking on a live phone call: answer in at most two short "
    "spoken sentences, plain words, no lists, no markdown, no emojis. Never mention being an AI "
    "or lacking context. If you do not know a detail, say a Relationship Manager will confirm it. "
    "End with one short question that moves the caller forward."
)


def _has_word(text: str, *phrases: str) -> bool:
    """True if any phrase appears as a whole word (case-insensitive)."""
    pattern = r"\b(?:" + "|".join(re.escape(p) for p in phrases) + r")\b"
    return re.search(pattern, text, re.IGNORECASE) is not None

def analyze_intent_node(state: AgentState) -> Dict[str, Any]:
    """
    Analyzes the latest user message to determine routing.
    Sets the 'current_node' to control flow.
    """
    messages = state.get("messages", [])
    if not messages:
        return {"current_node": "pitch_node"}
    
    last_message = messages[-1].content
    
    # Simple heuristic routing for now (can be upgraded to LLM-based structured output)
    if "?" in last_message or _has_word(last_message, "how", "what"):
        return {"current_node": "rag_node"}
    elif _has_word(last_message, "expensive", "not interested", "no"):
        return {"current_node": "objection_handler_node"}
    else:
        return {"current_node": "pitch_node"}

async def pitch_node(state: AgentState) -> Dict[str, Any]:
    """
    Standard pitch node.
    """
    system_prompt = SystemMessage(content=PERSONA + " Pitch the program naturally based on what was said so far. " + reply_language_instruction(state.get("lead_language")))
    
    response = await llm.ainvoke([system_prompt] + state["messages"])
    
    return {"messages": [response], "current_node": "scoring_node"}

async def rag_node(state: AgentState) -> Dict[str, Any]:
    """
    Retrieval-Augmented Generation node to answer specific questions.
    """
    kb_content = state.get("kb_context", "")
    
    if kb_content:
        prompt_text = (
            PERSONA + " The caller asked a specific question. Answer it from this knowledge "
            "base context where relevant:\n\n" + kb_content
        )
    else:
        prompt_text = PERSONA + " The caller asked a question: answer briefly from general knowledge of the program."

    system_prompt = SystemMessage(content=prompt_text + " " + reply_language_instruction(state.get("lead_language")))
    
    response = await llm.ainvoke([system_prompt] + state["messages"])
    
    return {"messages": [response], "current_node": "scoring_node"}

async def objection_handler_node(state: AgentState) -> Dict[str, Any]:
    """
    Handles objections raised by the user.
    """
    system_prompt = SystemMessage(content=PERSONA + " The caller raised an objection: acknowledge it with empathy, then give one concrete benefit. " + reply_language_instruction(state.get("lead_language")))
    
    objections = state.get("detected_objections", [])
    objections.append(state["messages"][-1].content)
    
    response = await llm.ainvoke([system_prompt] + state["messages"])
    
    return {"messages": [response], "detected_objections": objections, "current_node": "scoring_node"}

def scoring_node(state: AgentState) -> Dict[str, Any]:
    """
    Background node that evaluates sentiment/outcome without returning a message to the user.
    """
    messages = state.get("messages", [])
    if len(messages) < 2:
        return {"outcome": "UNKNOWN"}
    
    # Score the whole call: the newest decisive statement from the caller wins
    user_texts = [m.content for m in reversed(messages) if isinstance(m, HumanMessage)]
    outcome = classify_outcome(user_texts)
        
    return {"outcome": outcome, "current_node": "end"}
