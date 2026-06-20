import json
from typing import Optional, AsyncIterator, Sequence, Tuple, Any
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    AsyncBaseCheckpointSaver,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    SerializerProtocol
)
from services.database.repository import Repository
from services.database.supabase_client import get_db_client

class SupabaseCallSessionCheckpointer(AsyncBaseCheckpointSaver):
    """
    Custom LangGraph Checkpointer that reads and writes conversation state
    directly to the existing `call_sessions` table in Supabase.
    
    The config['configurable']['thread_id'] must correspond to the call_session.id.
    """
    
    def __init__(self, serde: Optional[SerializerProtocol] = None):
        super().__init__(serde=serde)

    async def get_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        """Fetch the state from Supabase call_sessions table."""
        session_id = config["configurable"]["thread_id"]
        
        db = await get_db_client()
        repo = Repository(db)
        
        # Get the session from DB
        session = await repo.get_call_session(session_id)
        if not session:
            return None
            
        # We manually reconstruct a LangGraph Checkpoint from our DB schema
        # In a real deep LangGraph integration, we'd store the raw serialized checkpoint,
        # but since we are mapping to `call_sessions.conversation_history`, we reconstruct it.
        checkpoint = Checkpoint(
            v=1,
            id=session_id,
            ts=session.get("created_at", ""),
            channel_values={
                "messages": session.get("conversation_history", []),
                "session_id": session_id,
                "lead_id": str(session.get("lead_id", "")),
                "lead_language": session.get("language_detected", "en"),
            },
            channel_versions={},
            versions_seen={},
            pending_sends=[]
        )
        
        return CheckpointTuple(
            config=config,
            checkpoint=checkpoint,
            metadata={}
        )

    async def list(self, config: Optional[RunnableConfig], *, filter: Optional[dict[str, Any]] = None, before: Optional[RunnableConfig] = None, limit: Optional[int] = None) -> AsyncIterator[CheckpointTuple]:
        """Not strictly needed for basic operation, but required by interface."""
        yield  # type: ignore

    async def put(self, config: RunnableConfig, checkpoint: Checkpoint, metadata: CheckpointMetadata, new_versions: dict[str, str]) -> RunnableConfig:
        """Write the updated state back to Supabase call_sessions table."""
        session_id = config["configurable"]["thread_id"]
        
        # Extract the latest messages from the checkpoint
        messages = checkpoint["channel_values"].get("messages", [])
        
        # We only want to persist primitive dicts to the DB, not Langchain message objects.
        # So we serialize them if they are objects.
        serialized_messages = []
        for msg in messages:
            if hasattr(msg, "dict"):
                serialized_messages.append(msg.dict())
            elif isinstance(msg, dict):
                serialized_messages.append(msg)
                
        db = await get_db_client()
        repo = Repository(db)
        
        # Update the conversation history in the database
        await db.execute(
            "UPDATE call_sessions SET conversation_history = $1 WHERE id = $2",
            json.dumps(serialized_messages),
            session_id
        )
        
        return {
            "configurable": {
                "thread_id": session_id,
                "checkpoint_id": checkpoint["id"],
            }
        }
    
    async def put_writes(self, config: RunnableConfig, writes: Sequence[Tuple[str, Any]], task_id: str) -> None:
        """Required by newer LangGraph versions for pending writes."""
        pass
