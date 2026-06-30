from typing import Dict, Any
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from orchestration.state import AgentState, llm

def analyze_intent_node(state: AgentState) -> Dict[str, Any]:
    """
    Analyzes the latest user message to determine routing.
    Sets the 'current_node' to control flow.
    """
    messages = state.get("messages", [])
    if not messages:
        return {"current_node": "pitch_node"}
    
    last_message = messages[-1].content.lower()
    
    # Simple heuristic routing for now (can be upgraded to LLM-based structured output)
    if "?" in last_message or "how" in last_message or "what" in last_message:
        return {"current_node": "rag_node"}
    elif "expensive" in last_message or "not interested" in last_message or "no" in last_message:
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
        
    last_user_message = messages[-2].content.lower() if isinstance(messages[-2], HumanMessage) else ""
    
    if "yes" in last_user_message or "interested" in last_user_message:
        outcome = "HOT"
    elif "no" in last_user_message or "stop" in last_user_message:
        outcome = "COLD"
    else:
        outcome = "WARM"
        
    return {"outcome": outcome, "current_node": "end"}
