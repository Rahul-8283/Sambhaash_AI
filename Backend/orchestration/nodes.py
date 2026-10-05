from typing import Dict, Any
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from orchestration.state import AgentState, llm
from orchestration.outcome import classify_outcome
import re

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

def pitch_node(state: AgentState) -> Dict[str, Any]:
    """
    Standard pitch node.
    """
    system_prompt = SystemMessage(content="You are Sambhaash AI, an expert sales agent. Pitch the product naturally and persuasively based on previous context.")
    
    response = llm.invoke([system_prompt] + state["messages"])
    
    return {"messages": [response], "current_node": "scoring_node"}

def rag_node(state: AgentState) -> Dict[str, Any]:
    """
    Retrieval-Augmented Generation node to answer specific questions.
    """
    kb_content = state.get("kb_context", "")
    
    prompt_text = (
        "You are Sambhaash AI. The user asked a specific question. "
        "Answer it concisely based ONLY on the following knowledge base context:\n\n"
        f"{kb_content}"
    )
    
    system_prompt = SystemMessage(content=prompt_text)
    
    response = llm.invoke([system_prompt] + state["messages"])
    
    return {"messages": [response], "current_node": "scoring_node"}

def objection_handler_node(state: AgentState) -> Dict[str, Any]:
    """
    Handles objections raised by the user.
    """
    system_prompt = SystemMessage(content="You are Sambhaash AI. The user has raised an objection. Handle it with empathy and provide a strong counter-value proposition.")
    
    objections = state.get("detected_objections", [])
    objections.append(state["messages"][-1].content)
    
    response = llm.invoke([system_prompt] + state["messages"])
    
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
