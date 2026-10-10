from typing import TypedDict, List, Annotated
import operator
from langchain_core.messages import BaseMessage
from langchain_groq import ChatGroq
from config import get_config

config = get_config()

# Shared Groq model instance. Model and token cap come from config so a model
# retirement is an env change, not a code change.
llm = ChatGroq(
    temperature=0.6,
    model_name=config.llm_model_name,
    max_tokens=config.llm_max_tokens,
    timeout=15,
    max_retries=1,
    api_key=config.groq_api_key
)

class AgentState(TypedDict):
    """
    Represents the complete conversational state of a single phone call.
    This state gets persisted to Supabase after every node execution.
    """
    
    # Annotated with operator.add so new messages are appended to the existing list
    messages: Annotated[List[BaseMessage], operator.add]
    
    # Contextual data
    session_id: str
    lead_id: str
    lead_name: str
    lead_language: str
    kb_context: str
    
    # Conversation intelligence
    detected_objections: List[str]
    current_node: str
    
    # Call outcome
    sentiment: str
    outcome: str
