"""
KB Context Injection Service
Retrieves and formats knowledge base context for call interactions.
Injects relevant KB articles into LLM prompts for better responses.
"""

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID
import json

from config import settings
from services.database.supabase_client import get_db_client
from services.database.repository import Repository
from services.llm.embedder import EmbedderService
from services.llm.rag_engine import RAGEngine

logger = logging.getLogger(__name__)


class KBContextInjectionService:
    """
    Retrieves KB context for calls and formats for LLM injection.
    
    Purpose:
    - Query knowledge base for relevant articles
    - Rank by relevance and confidence
    - Format for prompt injection
    - Track which articles are used in each call
    """
    
    def __init__(self, db_client=None, rag_engine: Optional[RAGEngine] = None):
        """
        Initialize KB context service.
        
        Args:
            db_client: Database client (lazy loaded if None)
            rag_engine: RAG engine for retrieval (lazy loaded if None)
        """
        self.db_client = db_client
        self.rag_engine = rag_engine
        self.repository: Optional[Repository] = None
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Lazy initialization of database and RAG engine."""
        if self._initialized:
            return
        
        if not self.db_client:
            self.db_client = await get_db_client()
        
        if not self.repository:
            self.repository = Repository(self.db_client)
        
        if not self.rag_engine:
            self.rag_engine = RAGEngine()
        
        self._initialized = True
    
    async def retrieve_context_for_call(
        self,
        call_session_id: UUID,
        lead_id: UUID,
        user_text: str,
        language: str = "en",
        top_k: int = 3,
        min_score: float = 0.3
    ) -> Dict[str, Any]:
        """
        Retrieve KB context for a call turn.
        
        Args:
            call_session_id: Current call session ID
            lead_id: Lead ID for context
            user_text: User's message (for semantic search)
            language: Detected language
            top_k: Number of top articles to retrieve
            min_score: Minimum relevance score threshold
        
        Returns:
            Dict with:
                - context_blocks: List of formatted KB chunks
                - doc_ids_used: List of document IDs used
                - relevance_scores: Scores for each chunk
                - total_tokens: Approximate token count
                - formatted_context: Pre-formatted string for injection
        """
        await self._ensure_initialized()
        
        try:
            logger.info(f"[KB_CTX] Retrieving context for call {call_session_id}, lead {lead_id}")
            
            # 1. Generate Embedding for User Query
            embedder = EmbedderService()
            query_embedding = embedder.embed_text(user_text)
            
            # 2. Query knowledge base for relevant chunks using pgvector
            logger.debug(f"[KB_CTX] Running vector search for: {user_text[:30]}")
            search_results = await self.repository.vector_search_knowledge_base(
                query_embedding=query_embedding,
                top_k=top_k
            )
            
            if not search_results:
                logger.info(f"[KB_CTX] No KB results for query: {user_text[:50]}")
                return {
                    "context_blocks": [],
                    "doc_ids_used": [],
                    "relevance_scores": [],
                    "total_tokens": 0,
                    "formatted_context": "",
                    "kb_available": False
                }
            
            logger.info(f"[KB_CTX] Retrieved {len(search_results)} KB chunks")
            
            # 2. Format context blocks
            context_blocks = []
            doc_ids_used = []
            relevance_scores = []
            total_tokens = 0
            
            for i, result in enumerate(search_results, 1):
                chunk_id = result.get("id")
                doc_id = result.get("document_id")
                chunk_text = result.get("text")
                score = result.get("score", 0.0)
                doc_title = result.get("file_name", "Unknown Document")
                chunk_number = result.get("source_section") or 0
                
                # Format chunk
                context_block = {
                    "rank": i,
                    "chunk_id": str(chunk_id),
                    "doc_id": str(doc_id),
                    "title": doc_title,
                    "chunk_number": chunk_number,
                    "text": chunk_text,
                    "relevance_score": round(float(score), 3)
                }
                
                context_blocks.append(context_block)
                doc_ids_used.append(str(doc_id))
                relevance_scores.append(float(score))
                total_tokens += len(chunk_text.split()) * 1.3  # Approximate tokenization
            
            # 3. Format for injection into prompt
            formatted_context = self._format_context_for_prompt(context_blocks)
            
            # 4. Store KB context usage in call session
            await self._log_kb_usage(
                call_session_id=call_session_id,
                doc_ids_used=doc_ids_used,
                relevance_scores=relevance_scores,
                user_query=user_text
            )
            
            logger.info(f"[KB_CTX] Formatted context ({len(context_blocks)} chunks, ~{int(total_tokens)} tokens)")
            
            return {
                "context_blocks": context_blocks,
                "doc_ids_used": doc_ids_used,
                "relevance_scores": relevance_scores,
                "total_tokens": int(total_tokens),
                "formatted_context": formatted_context,
                "kb_available": True
            }
        
        except Exception as e:
            logger.error(f"[KB_CTX] Error retrieving context: {e}", exc_info=True)
            return {
                "context_blocks": [],
                "doc_ids_used": [],
                "relevance_scores": [],
                "total_tokens": 0,
                "formatted_context": "",
                "kb_available": False,
                "error": str(e)
            }
    
    def _format_context_for_prompt(self, context_blocks: List[Dict]) -> str:
        """
        Format KB context blocks for LLM injection.
        
        Args:
            context_blocks: List of context blocks
        
        Returns:
            Formatted string for prompt injection
        """
        if not context_blocks:
            return ""
        
        lines = [
            "=== RELEVANT KNOWLEDGE BASE ARTICLES ===",
            ""
        ]
        
        for block in context_blocks:
            title = block.get("title", "Unknown")
            text = block.get("text", "")
            score = block.get("relevance_score", 0.0)
            rank = block.get("rank", 1)
            
            # Format each block
            lines.append(f"[Article {rank} - Relevance: {score:.1%}]")
            lines.append(f"Source: {title}")
            lines.append("-" * 40)
            lines.append(text[:300] + ("..." if len(text) > 300 else ""))
            lines.append("")
        
        lines.append("=== END KNOWLEDGE BASE CONTEXT ===")
        lines.append("")
        lines.append("Use the above knowledge base articles to inform your response.")
        lines.append("If relevant information is in the KB, cite which article you're using.")
        
        return "\n".join(lines)
    
    async def _log_kb_usage(
        self,
        call_session_id: UUID,
        doc_ids_used: List[str],
        relevance_scores: List[float],
        user_query: str
    ):
        """
        Log KB usage for analytics.
        
        Args:
            call_session_id: Call session ID
            doc_ids_used: List of document IDs used
            relevance_scores: Relevance scores for each doc
            user_query: User's query that triggered KB search
        """
        try:
            await self._ensure_initialized()
            
            # Get current call session
            session = await self.repository.get_call_session(call_session_id)
            if not session:
                logger.warning(f"[KB_CTX] Session not found: {call_session_id}")
                return
            
            # Parse existing KB usage log
            kb_usage = json.loads(session.get("kb_usage_log", "[]"))
            
            # Add new usage entry
            usage_entry = {
                "timestamp": str(__import__('datetime').datetime.utcnow()),
                "query": user_query[:100],  # Truncate
                "documents_used": doc_ids_used,
                "relevance_scores": [round(s, 3) for s in relevance_scores]
            }
            kb_usage.append(usage_entry)
            
            # Update session with KB usage log
            await self.repository.update_call_session(
                session_id=call_session_id,
                kb_usage_log=kb_usage
            )
            
            logger.debug(f"[KB_CTX] Logged KB usage for session {call_session_id}")
        
        except Exception as e:
            logger.error(f"[KB_CTX] Error logging KB usage: {e}")
    
    async def get_kb_analytics_for_call(self, call_session_id: UUID) -> Dict[str, Any]:
        """
        Get analytics of KB usage for a call.
        
        Args:
            call_session_id: Call session ID
        
        Returns:
            Dict with analytics about KB usage during this call
        """
        try:
            await self._ensure_initialized()
            
            session = await self.repository.get_call_session(call_session_id)
            if not session:
                return {"error": "Session not found"}
            
            kb_usage = json.loads(session.get("kb_usage_log", "[]"))
            
            if not kb_usage:
                return {
                    "total_queries": 0,
                    "total_documents_used": 0,
                    "avg_relevance_score": 0.0,
                    "documents_list": []
                }
            
            # Aggregate analytics
            all_docs = []
            all_scores = []
            
            for entry in kb_usage:
                all_docs.extend(entry.get("documents_used", []))
                all_scores.extend(entry.get("relevance_scores", []))
            
            unique_docs = list(set(all_docs))
            avg_score = sum(all_scores) / len(all_scores) if all_scores else 0.0
            
            return {
                "total_queries": len(kb_usage),
                "total_documents_used": len(all_docs),
                "unique_documents": len(unique_docs),
                "avg_relevance_score": round(avg_score, 3),
                "documents_list": unique_docs,
                "usage_log": kb_usage
            }
        
        except Exception as e:
            logger.error(f"[KB_CTX] Error getting analytics: {e}")
            return {"error": str(e)}


# Global instance for dependency injection
_kb_context_service: Optional[KBContextInjectionService] = None


async def get_kb_context_service() -> KBContextInjectionService:
    """Get or create KB context injection service."""
    global _kb_context_service
    if _kb_context_service is None:
        _kb_context_service = KBContextInjectionService()
    return _kb_context_service
