from langgraph.graph import StateGraph, END
from typing import Dict, Any

from orchestration.state import AgentState
from orchestration.nodes import (
    analyze_intent_node,
    pitch_node,
    rag_node,
    objection_handler_node,
    scoring_node
)

# Initialize the StateGraph with our defined AgentState
workflow = StateGraph(AgentState)

# Add all our nodes to the graph
workflow.add_node("analyze_intent_node", analyze_intent_node)
workflow.add_node("pitch_node", pitch_node)
workflow.add_node("rag_node", rag_node)
workflow.add_node("objection_handler_node", objection_handler_node)
workflow.add_node("scoring_node", scoring_node)

# Set the entry point. Every conversation turn starts by analyzing the user's intent.
workflow.set_entry_point("analyze_intent_node")

def route_intent(state: AgentState) -> str:
    """
    Conditional routing function based on the output of the Analyze Intent Node.
    """
    # The analyze_intent_node sets 'current_node' to tell us where to go next
    return state.get("current_node", "pitch_node")

# Add conditional edges from the starting node
workflow.add_conditional_edges(
    "analyze_intent_node",
    route_intent,
    {
        "rag_node": "rag_node",
        "objection_handler_node": "objection_handler_node",
        "pitch_node": "pitch_node",
    }
)

# After any generation node, we always score the outcome in the background
workflow.add_edge("rag_node", "scoring_node")
workflow.add_edge("objection_handler_node", "scoring_node")
workflow.add_edge("pitch_node", "scoring_node")

# The scoring node is the end of this single conversational turn
workflow.add_edge("scoring_node", END)

# Compile without a checkpointer. Conversation memory is rebuilt from the
# call's stored turns on every invocation (see orchestration/history.py). The old
# checkpointer restored empty messages and collided with the same DB column.
app = workflow.compile()
