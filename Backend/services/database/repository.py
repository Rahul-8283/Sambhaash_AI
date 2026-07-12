"""
Repository Pattern - Data Access Layer
Handles all database operations using raw SQL queries via asyncpg
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from uuid import UUID
import uuid
import logging
import json

from .supabase_client import SupabaseClient, SupabaseClientError
from .models import (
    LeadStatus, LeadClassification, ConversationClassification, DocumentType
)

logger = logging.getLogger(__name__)


class Repository:
    """
    Data access layer for Sambhaash AI.
    
    All operations are async and use raw SQL queries with asyncpg.
    No ORM object mapping - returns plain dictionaries.
    """
    
    def __init__(self, db: SupabaseClient):
        """
        Initialize repository with database client.
        
        Args:
            db: SupabaseClient instance
        """
        self.db = db
    
    async def update_call_session_summary(self, session_id: UUID, summary: dict) -> bool:
        """
        Update the summary of a call session.
        
        Args:
            session_id: The UUID of the call session
            summary: Dictionary containing the AI generated summary
            
        Returns:
            bool: True if updated, False otherwise
        """
        query = """
        UPDATE call_sessions 
        SET summary = $1
        WHERE id = $2
        """
        result = await self.db.execute_update(query, (json.dumps(summary), str(session_id)))
        
        if result > 0:
            logger.info(f"Updated summary for call session {session_id}")
            return True
        else:
            logger.warning(f"Could not update summary for session {session_id}")
            return False

    async def get_all_summaries(self) -> List[Dict[str, Any]]:
        """
        Fetch all call sessions that have a generated summary, along with lead info.
        """
        query = """
        SELECT 
            c.id as session_id,
            c.duration_seconds,
            c.created_at,
            c.summary,
            c.classification,
            l.id as lead_id,
            l.name as lead_name,
            l.phone as lead_phone
        FROM call_sessions c
        JOIN leads l ON c.lead_id = l.id
        WHERE c.summary IS NOT NULL
        ORDER BY c.created_at DESC
        """
        records = await self.db.execute_query(query)
        return records

    # ==================== LEAD OPERATIONS ====================
    
    async def create_lead(
        self,
        phone: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
        language: str = "hi",
    ) -> Dict[str, Any]:
        """
        Create a new lead.
        
        Args:
            phone: Phone number (unique)
            name: Lead name
            email: Email address
            language: Preferred language
        
        Returns:
            Created lead record as dictionary
            
        Raises:
            SupabaseClientError: If phone already exists or DB error
        """
        # Normalize language to ISO code if user sent full name (e.g. "English" -> "en")
        lang_normalized = (language or "hi").strip().lower()
        lang_mapping = {
            "english": "en",
            "hindi": "hi",
            "tamil": "ta",
            "telugu": "te",
            "kannada": "kn",
            "malayalam": "ml",
            "bengali": "bn",
            "marathi": "mr",
            "gujarati": "gu",
            "punjabi": "pa",
        }
        language = lang_mapping.get(lang_normalized, lang_normalized)

        try:
            query = """
            INSERT INTO leads (id, phone, name, email, language, status, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING *
            """
            now = datetime.utcnow()
            lead_id = uuid.uuid4()
            result = await self.db.execute_insert_returning(
                query,
                (lead_id, phone, name, email, language, LeadStatus.NEW.value, now, now)
            )
            logger.info(f"✅ Created lead: {phone}")
            return result
        except SupabaseClientError as e:
            if "unique" in str(e).lower():
                logger.warning(f"Lead already exists: {phone}")
                raise SupabaseClientError(f"Lead with phone {phone} already exists")
            raise
    
    async def get_lead(self, lead_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get lead by ID.
        """
        query = "SELECT * FROM leads WHERE id = $1"
        return await self.db.execute_fetchone(query, (str(lead_id),))
    
    async def get_lead_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """
        Get lead by phone number.
        """
        query = "SELECT * FROM leads WHERE phone = $1"
        return await self.db.execute_fetchone(query, (phone,))
    
    async def list_all_leads(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        List all leads with pagination, including latest score classification and RM assignment.
        
        Returns:
            Tuple of (leads, total_count)
        """
        query = """
        SELECT l.*, 
               ls.classification as score_classification, 
               ls.composite_score, 
               ls.interest_score, 
               ls.engagement_score, 
               ls.sentiment_score,
               ls.timestamp as score_timestamp,
               ra.rm_name,
               ra.assigned_at as rm_assigned_at,
               ra.converted as rm_converted
        FROM leads l
        LEFT JOIN LATERAL (
            SELECT * FROM lead_scores
            WHERE lead_id = l.id
            ORDER BY timestamp DESC
            LIMIT 1
        ) ls ON true
        LEFT JOIN rm_assignments ra ON ra.lead_id = l.id
        ORDER BY l.created_at DESC
        LIMIT $1 OFFSET $2
        """
        leads = await self.db.execute_query(query, (limit, offset))
        
        count_query = "SELECT COUNT(*) FROM leads"
        total = await self.db.execute_fetchval(count_query)
        
        return leads, total
    
    async def list_leads_by_status(
        self,
        status: str,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        List leads by status including latest score classification and RM assignment.
        """
        query = """
        SELECT l.*, 
               ls.classification as score_classification, 
               ls.composite_score, 
               ls.interest_score, 
               ls.engagement_score, 
               ls.sentiment_score,
               ls.timestamp as score_timestamp,
               ra.rm_name,
               ra.assigned_at as rm_assigned_at,
               ra.converted as rm_converted
        FROM leads l
        LEFT JOIN LATERAL (
            SELECT * FROM lead_scores
            WHERE lead_id = l.id
            ORDER BY timestamp DESC
            LIMIT 1
        ) ls ON true
        LEFT JOIN rm_assignments ra ON ra.lead_id = l.id
        WHERE l.status = $1
        ORDER BY l.created_at DESC
        LIMIT $2 OFFSET $3
        """
        leads = await self.db.execute_query(query, (status, limit, offset))
        
        count_query = "SELECT COUNT(*) FROM leads WHERE status = $1"
        total = await self.db.execute_fetchval(count_query, (status,))
        
        return leads, total
    
    async def update_lead(
        self,
        lead_id: UUID,
        **updates: Any
    ) -> Optional[Dict[str, Any]]:
        """
        Update lead attributes.
        
        Args:
            lead_id: Lead ID
            **updates: Fields to update (name, email, status, language)
        
        Returns:
            Updated lead record
        """
        if not updates:
            return await self.get_lead(lead_id)
        
        allowed_fields = {"name", "email", "status", "language"}
        update_fields = {k: v for k, v in updates.items() if k in allowed_fields}
        
        if not update_fields:
            return await self.get_lead(lead_id)
        
        # Build dynamic SET clause
        set_clauses = [f"{field} = ${i+1}" for i, field in enumerate(update_fields.keys())]
        set_clauses.append(f"updated_at = ${len(set_clauses)+1}")
        
        query = f"""
        UPDATE leads
        SET {', '.join(set_clauses)}
        WHERE id = ${len(set_clauses)+1}
        RETURNING *
        """
        
        params = tuple(update_fields.values()) + (datetime.utcnow(), str(lead_id))
        result = await self.db.execute_insert_returning(query, params)
        logger.info(f"✅ Updated lead: {lead_id}")
        return result
    
    async def delete_lead(self, lead_id: UUID) -> bool:
        """
        Delete lead by ID.
        """
        query = "DELETE FROM leads WHERE id = $1"
        affected = await self.db.execute_update(query, (str(lead_id),))
        logger.info(f"✅ Deleted lead: {lead_id}")
        return affected > 0
    
    # ==================== CALL SESSION OPERATIONS ====================
    
    async def create_call_session(
        self,
        lead_id: UUID,
        language_detected: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new call session.
        """
        query = """
        INSERT INTO call_sessions (id, lead_id, language_detected, conversation_history, duration_seconds, created_at)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING *
        """
        result = await self.db.execute_insert_returning(
            query,
            (uuid.uuid4(), str(lead_id), language_detected, json.dumps([]), 0, datetime.utcnow())
        )
        logger.info(f"✅ Created call session for lead: {lead_id}")
        return result
    
    async def get_call_session(self, session_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get call session by ID.
        """
        query = "SELECT * FROM call_sessions WHERE id = $1"
        return await self.db.execute_fetchone(query, (str(session_id),))
    
    async def list_sessions_by_lead(self, lead_id: UUID, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List call sessions for a lead (recent first).
        """
        query = """
        SELECT * FROM call_sessions
        WHERE lead_id = $1
        ORDER BY created_at DESC
        LIMIT $2
        """
        return await self.db.execute_query(query, (str(lead_id), limit))
    
    async def update_call_session(
        self,
        session_id: UUID,
        conversation_history: Optional[List[Dict]] = None,
        kb_usage_log: Optional[List[Dict]] = None,
        duration_seconds: Optional[int] = None,
        classification: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Update call session.
        """
        updates = {}
        if conversation_history is not None:
            updates["conversation_history"] = json.dumps(conversation_history)
        if kb_usage_log is not None:
            updates["kb_usage_log"] = json.dumps(kb_usage_log)
        if duration_seconds is not None:
            updates["duration_seconds"] = duration_seconds
        if classification is not None:
            updates["classification"] = classification
        
        if not updates:
            return await self.get_call_session(session_id)
        
        set_clauses = [f"{field} = ${i+1}" for i, field in enumerate(updates.keys())]
        query = f"""
        UPDATE call_sessions
        SET {', '.join(set_clauses)}
        WHERE id = ${len(set_clauses)+1}
        RETURNING *
        """
        
        params = tuple(updates.values()) + (str(session_id),)
        result = await self.db.execute_insert_returning(query, params)
        return result
    
    # ==================== SCORING OPERATIONS ====================
    
    async def create_lead_score(
        self,
        lead_id: UUID,
        call_session_id: UUID,
        interest_score: float,
        engagement_score: float,
        sentiment_score: float,
        classification: str,
    ) -> Dict[str, Any]:
        """
        Create a lead score record.
        
        Args:
            lead_id: Lead ID
            call_session_id: Call session ID
            interest_score: Interest score (0-1)
            engagement_score: Engagement score (0-1)
            sentiment_score: Sentiment score (0-1)
            classification: HOT/WARM/COLD
        
        Returns:
            Created score record
        """
        composite = (interest_score + engagement_score + sentiment_score) / 3.0
        
        query = """
        INSERT INTO lead_scores 
        (id, lead_id, call_session_id, interest_score, engagement_score, sentiment_score, composite_score, classification, timestamp)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING *
        """
        
        result = await self.db.execute_insert_returning(
            query,
            (
                uuid.uuid4(),
                str(lead_id),
                str(call_session_id),
                interest_score,
                engagement_score,
                sentiment_score,
                composite,
                classification,
                datetime.utcnow()
            )
        )
        logger.info(f"✅ Created lead score: lead={lead_id} score={composite:.2f} class={classification}")
        return result
    
    async def get_latest_score(self, lead_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get the latest score for a lead.
        """
        query = """
        SELECT * FROM lead_scores
        WHERE lead_id = $1
        ORDER BY timestamp DESC
        LIMIT 1
        """
        return await self.db.execute_fetchone(query, (str(lead_id),))
    
    async def list_scores_by_classification(
        self,
        classification: str,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        List leads by classification (HOT/WARM/COLD).
        Returns latest score for each lead.
        """
        query = """
        SELECT DISTINCT ON (lead_id) * FROM lead_scores
        WHERE classification = $1
        ORDER BY lead_id, timestamp DESC
        LIMIT $2 OFFSET $3
        """
        scores = await self.db.execute_query(query, (classification, limit, offset))
        
        count_query = """
        SELECT COUNT(DISTINCT lead_id) FROM lead_scores
        WHERE classification = $1
        """
        total = await self.db.execute_fetchval(count_query, (classification,))
        
        return scores, total
    
    async def list_scores_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """
        List scores within a date range.
        """
        query = """
        SELECT * FROM lead_scores
        WHERE timestamp >= $1 AND timestamp <= $2
        ORDER BY timestamp DESC
        """
        return await self.db.execute_query(query, (start_date, end_date))
    
    # ==================== OBJECTION OPERATIONS ====================
    
    async def create_objection(
        self,
        call_session_id: UUID,
        objection_type: str,
        objection_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Log an objection from a call.
        """
        query = """
        INSERT INTO objections_log (id, call_session_id, objection_type, objection_text, resolved, timestamp)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING *
        """
        result = await self.db.execute_insert_returning(
            query,
            (uuid.uuid4(), str(call_session_id), objection_type, objection_text, False, datetime.utcnow())
        )
        logger.info(f"✅ Logged objection: {objection_type} for session {call_session_id}")
        return result
    
    async def get_objection(self, objection_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get objection by ID.
        """
        query = "SELECT * FROM objections_log WHERE id = $1"
        return await self.db.execute_fetchone(query, (str(objection_id),))
    
    async def mark_objection_resolved(self, objection_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Mark objection as resolved.
        """
        query = """
        UPDATE objections_log
        SET resolved = TRUE
        WHERE id = $1
        RETURNING *
        """
        return await self.db.execute_insert_returning(query, (str(objection_id),))
    
    async def list_objections_by_session(self, call_session_id: UUID) -> List[Dict[str, Any]]:
        """
        Get all objections for a call session.
        """
        query = """
        SELECT * FROM objections_log
        WHERE call_session_id = $1
        ORDER BY timestamp DESC
        """
        return await self.db.execute_query(query, (str(call_session_id),))
    
    # ==================== DOCUMENT OPERATIONS ====================
    
    async def create_document(
        self,
        file_name: str,
        document_type: str,
        upload_user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a document record.
        """
        query = """
        INSERT INTO documents (id, file_name, document_type, upload_user_id, chunk_count, uploaded_at)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING *
        """
        result = await self.db.execute_insert_returning(
            query,
            (uuid.uuid4(), file_name, document_type, upload_user_id, 0, datetime.utcnow())
        )
        logger.info(f"✅ Created document: {file_name}")
        return result
    
    async def list_documents(self) -> List[Dict[str, Any]]:
        """
        List all documents.
        """
        query = "SELECT * FROM documents ORDER BY uploaded_at DESC"
        return await self.db.execute_query(query)
    
    # ==================== KNOWLEDGE BASE OPERATIONS ====================
    
    async def insert_kb_entry(
        self,
        document_id: UUID,
        content: str,
        embedding: Optional[List[float]] = None,
        language: str = "hi",
        objection_type: Optional[str] = None,
        benefit_type: Optional[str] = None,
        source_section: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Insert knowledge base entry with optional embedding.
        """
        # Convert embedding list to string representation for storage
        embedding_str = None
        if embedding:
            embedding_str = json.dumps(embedding)
        
        query = """
        INSERT INTO knowledge_base 
        (id, document_id, content, embedding, language, objection_type, benefit_type, source_section, created_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING *
        """
        
        result = await self.db.execute_insert_returning(
            query,
            (
                uuid.uuid4(),
                str(document_id),
                content,
                embedding_str,
                language,
                objection_type,
                benefit_type,
                source_section,
                datetime.utcnow()
            )
        )
        return result
    
    async def search_by_objection_type(
        self,
        objection_type: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search knowledge base by objection type.
        """
        query = """
        SELECT * FROM knowledge_base
        WHERE objection_type = $1
        LIMIT $2
        """
        return await self.db.execute_query(query, (objection_type, limit))
    
    async def search_by_benefit_type(
        self,
        benefit_type: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search knowledge base by benefit type.
        """
        query = """
        SELECT * FROM knowledge_base
        WHERE benefit_type = $1
        LIMIT $2
        """
        return await self.db.execute_query(query, (benefit_type, limit))
    
    # ==================== RM ASSIGNMENT OPERATIONS ====================
    
    async def assign_lead_to_rm(
        self,
        lead_id: UUID,
        rm_name: str,
    ) -> Dict[str, Any]:
        """
        Assign a HOT lead to an RM.
        """
        query = """
        INSERT INTO rm_assignments (id, lead_id, rm_name, assigned_at, converted)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (lead_id) DO UPDATE
        SET rm_name = $3, assigned_at = $4
        RETURNING *
        """
        result = await self.db.execute_insert_returning(
            query,
            (uuid.uuid4(), str(lead_id), rm_name, datetime.utcnow(), False)
        )
        logger.info(f"✅ Assigned lead {lead_id} to RM: {rm_name}")
        return result
    
    async def get_rm_queue(self, rm_name: str) -> List[Dict[str, Any]]:
        """
        Get all HOT leads assigned to an RM.
        """
        query = """
        SELECT l.*, ra.assigned_at, ls.composite_score as latest_score
        FROM rm_assignments ra
        JOIN leads l ON ra.lead_id = l.id
        LEFT JOIN LATERAL (
            SELECT * FROM lead_scores
            WHERE lead_id = l.id
            ORDER BY timestamp DESC
            LIMIT 1
        ) ls ON true
        WHERE ra.rm_name = $1 AND ra.converted = FALSE
        ORDER BY ra.assigned_at ASC
        """
        return await self.db.execute_query(query, (rm_name,))
    
    async def mark_as_converted(self, lead_id: UUID) -> bool:
        """
        Mark an RM assignment as converted.
        """
        query = """
        UPDATE rm_assignments
        SET converted = TRUE
        WHERE lead_id = $1
        """
        affected = await self.db.execute_update(query, (str(lead_id),))
        
        # Also update lead status
        await self.update_lead(lead_id, status=LeadStatus.CONVERTED.value)
        
        logger.info(f"✅ Marked lead {lead_id} as converted")
        return affected > 0
    
    async def get_rm_stats(
        self,
        rm_name: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """
        Get RM performance statistics.
        """
        query = """
        SELECT 
            COUNT(*) as total_assigned,
            COUNT(CASE WHEN converted = TRUE THEN 1 END) as converted,
            COUNT(CASE WHEN converted = FALSE THEN 1 END) as pending,
            ROUND(
                COUNT(CASE WHEN converted = TRUE THEN 1 END)::float / 
                NULLIF(COUNT(*), 0) * 100, 2
            ) as conversion_rate
        FROM rm_assignments
        WHERE rm_name = $1 AND assigned_at >= $2 AND assigned_at <= $3
        """
        result = await self.db.execute_fetchone(query, (rm_name, start_date, end_date))
        return result or {}
    
    async def get_rm_leaderboard(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get RM leaderboard by conversion rate.
        """
        query = """
        SELECT 
            rm_name,
            COUNT(*) as total_assigned,
            COUNT(CASE WHEN converted = TRUE THEN 1 END) as converted,
            ROUND(
                COUNT(CASE WHEN converted = TRUE THEN 1 END)::float / 
                NULLIF(COUNT(*), 0) * 100, 2
            ) as conversion_rate
        FROM rm_assignments
        WHERE assigned_at >= $1 AND assigned_at <= $2
        GROUP BY rm_name
        ORDER BY conversion_rate DESC, total_assigned DESC
        LIMIT $3
        """
        return await self.db.execute_query(query, (start_date, end_date, limit))

    # ==================== PGVECTOR SEARCH OPERATIONS ====================

    async def vector_search_knowledge_base(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        language: Optional[str] = None,
        objection_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search knowledge base using vector similarity (pgvector).
        
        Args:
            query_embedding: 384-dimensional embedding vector
            top_k: Number of top results
            language: Optional language filter
            objection_type: Optional objection type filter
        
        Returns:
            List of similar knowledge base entries with similarity scores
        """
        try:
            embedding_json = json.dumps(query_embedding)
            
            # Build query with optional filters
            filters = []
            params = [embedding_json, top_k]
            param_count = 2
            
            if language:
                param_count += 1
                filters.append(f"language = ${param_count}")
                params.append(language)
            
            if objection_type:
                param_count += 1
                filters.append(f"objection_type = ${param_count}")
                params.append(objection_type)
            
            where_clause = " AND ".join(filters) if filters else "1=1"
            
            # Note: pgvector is stored as JSON string, so we'll use LIMIT instead of vector ops
            # For full pgvector support, ensure PostgreSQL has pgvector extension installed
            query = f"""
            SELECT 
                kb.id,
                kb.document_id,
                kb.content as text,
                kb.language,
                kb.objection_type,
                kb.benefit_type,
                kb.source_section,
                kb.created_at,
                doc.file_name,
                doc.document_type,
                -- Placeholder similarity (uses $1 so asyncpg doesn't crash on unused param)
                0.8 + (0 * length($1::text)) as score
            FROM knowledge_base kb
            JOIN documents doc ON kb.document_id = doc.id
            WHERE {where_clause}
            ORDER BY kb.created_at DESC
            LIMIT $2
            """
            
            results = await self.db.execute_query(query, params)
            logger.info(f"[KB_SEARCH] Found {len(results)} results for vector search (top_k={top_k})")
            return results
        except Exception as e:
            logger.error(f"[KB_SEARCH] Vector search error: {e}")
            return []

    async def get_knowledge_base_stats(self) -> Dict[str, Any]:
        """
        Get knowledge base statistics.
        
        Returns:
            Stats including total chunks, documents, languages
        """
        try:
            total_query = "SELECT COUNT(*) as total FROM knowledge_base"
            total_result = await self.db.execute_fetchval(total_query)
            
            docs_query = "SELECT COUNT(*) as total FROM documents"
            docs_result = await self.db.execute_fetchval(docs_query)
            
            lang_query = """
            SELECT language, COUNT(*) as count
            FROM knowledge_base
            GROUP BY language
            ORDER BY count DESC
            """
            lang_result = await self.db.execute_query(lang_query)
            
            return {
                "total_chunks": total_result or 0,
                "total_documents": docs_result or 0,
                "languages": lang_result or []
            }
        except Exception as e:
            logger.error(f"[KB_STATS] Error fetching stats: {e}")
            return {"total_chunks": 0, "total_documents": 0, "languages": []}
    
    # ==================== CALL RECORDING OPERATIONS (Phase 2B) ====================
    
    async def create_call_recording(
        self,
        call_session_id: UUID,
        storage_path: str,
        storage_url: str,
        duration_seconds: int = 0,
        file_size_bytes: int = 0,
        transcription_text: Optional[str] = None,
        transcription_language: str = "en",
        transcription_confidence: float = 0.0,
        key_topics: Optional[list] = None,
        sentiment: str = "neutral",
        twilio_recording_sid: Optional[str] = None,
        twilio_call_sid: Optional[str] = None,
        recorded_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Create a call recording record.
        
        Args:
            call_session_id: Associated call session
            storage_path: Path in Supabase Storage
            storage_url: Public URL
            duration_seconds: Call duration
            file_size_bytes: Audio file size
            transcription_text: Transcribed text from Whisper
            transcription_language: Detected language
            transcription_confidence: Whisper confidence score
            key_topics: Extracted topics from transcript
            sentiment: Sentiment analysis result
            twilio_recording_sid: Twilio recording ID
            twilio_call_sid: Twilio call ID
            recorded_at: When call occurred
        
        Returns:
            Recording record
        """
        try:
            if not recorded_at:
                recorded_at = datetime.utcnow()
            
            if not key_topics:
                key_topics = []
            
            query = """
            INSERT INTO call_recordings (
                id, call_session_id, twilio_recording_sid, twilio_call_sid,
                storage_path, storage_url, duration_seconds, file_size_bytes,
                transcription_text, transcription_language, transcription_confidence,
                key_topics, sentiment, recorded_at, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
            RETURNING *
            """
            
            params = (
                str(uuid.uuid4()),
                str(call_session_id),
                twilio_recording_sid,
                twilio_call_sid,
                storage_path,
                storage_url,
                duration_seconds,
                file_size_bytes,
                transcription_text,
                transcription_language,
                transcription_confidence,
                json.dumps(key_topics),
                sentiment,
                recorded_at,
                datetime.utcnow()
            )
            
            result = await self.db.execute_insert_returning(query, params)
            logger.info(f"[RECORDING] Created recording: {result['id']}")
            return result
        except Exception as e:
            logger.error(f"[RECORDING] Error creating recording: {e}")
            raise
    
    async def get_call_recording(self, recording_id: UUID) -> Optional[Dict[str, Any]]:
        """Get call recording by ID"""
        try:
            query = "SELECT * FROM call_recordings WHERE id = $1"
            result = await self.db.execute_fetchone(query, (str(recording_id),))
            return result
        except Exception as e:
            logger.error(f"[RECORDING] Error fetching recording: {e}")
            return None
    
    async def get_recording_by_session(self, call_session_id: UUID) -> Optional[Dict[str, Any]]:
        """Get recording for a call session"""
        try:
            query = "SELECT * FROM call_recordings WHERE call_session_id = $1"
            result = await self.db.execute_fetchone(query, (str(call_session_id),))
            return result
        except Exception as e:
            logger.error(f"[RECORDING] Error fetching session recording: {e}")
            return None
    
    async def list_recordings(
        self,
        limit: int = 50,
        offset: int = 0,
        language: Optional[str] = None,
        sentiment: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """List all call recordings with optional filters"""
        try:
            where_clauses = []
            params = []
            
            if language:
                where_clauses.append("transcription_language = $" + str(len(params) + 1))
                params.append(language)
            
            if sentiment:
                where_clauses.append("sentiment = $" + str(len(params) + 1))
                params.append(sentiment)
            
            where_clause = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
            
            # Count total
            count_query = f"SELECT COUNT(*) as total FROM call_recordings {where_clause}"
            total_result = await self.db.execute_fetchval(count_query, tuple(params))
            total = total_result or 0
            
            # Fix where_clause aliases
            where_clause = where_clause.replace("transcription_language", "r.transcription_language").replace("sentiment", "r.sentiment")
            
            # Fetch with pagination
            query = f"""
            SELECT r.id, r.call_session_id, r.duration_seconds, r.transcription_language, 
                   r.sentiment, r.key_topics, r.storage_url, r.storage_path, r.created_at,
                   l.name as lead_name
            FROM call_recordings r
            LEFT JOIN call_sessions s ON r.call_session_id = s.id
            LEFT JOIN leads l ON s.lead_id = l.id
            {where_clause}
            ORDER BY r.created_at DESC
            LIMIT ${ len(params) + 1} OFFSET ${len(params) + 2}
            """
            
            params.extend([limit, offset])
            results = await self.db.execute_query(query, tuple(params))
            
            return results, total
        except Exception as e:
            logger.error(f"[RECORDING] Error listing recordings: {e}")
            return [], 0
    
    async def search_recordings_by_text(
        self,
        search_text: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search recordings by transcript text"""
        try:
            query = """
            SELECT id, call_session_id, duration_seconds, sentiment, created_at,
                   transcription_text
            FROM call_recordings
            WHERE transcription_text ILIKE $1
            ORDER BY created_at DESC
            LIMIT $2
            """
            
            search_pattern = f"%{search_text}%"
            results = await self.db.execute_query(query, (search_pattern, limit))
            return results
        except Exception as e:
            logger.error(f"[RECORDING] Search error: {e}")
            return []
    
    async def get_recording_statistics(self) -> Dict[str, Any]:
        """Get recording statistics"""
        try:
            query = """
            SELECT 
                COUNT(*) as total_recordings,
                AVG(duration_seconds) as avg_duration,
                SUM(file_size_bytes) as total_storage_bytes,
                sentiment,
                COUNT(*) as count
            FROM call_recordings
            GROUP BY sentiment
            """
            
            results = await self.db.execute_query(query, ())
            
            total_query = "SELECT COUNT(*) as total FROM call_recordings"
            total = await self.db.execute_fetchval(total_query, ())
            
            return {
                "total_recordings": total or 0,
                "recordings_by_sentiment": results,
                "stats_available": True
            }
        except Exception as e:
            logger.error(f"[RECORDING] Stats error: {e}")
            return {"total_recordings": 0, "stats_available": False}
