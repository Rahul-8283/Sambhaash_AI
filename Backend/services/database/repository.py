"""
Repository Pattern - Data Access Layer
Handles all database operations using raw SQL queries via asyncpg
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from uuid import UUID
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
        try:
            query = """
            INSERT INTO leads (phone, name, email, language, status, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *
            """
            now = datetime.utcnow()
            result = await self.db.execute_insert_returning(
                query,
                (phone, name, email, language, LeadStatus.NEW.value, now, now)
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
        List all leads with pagination.
        
        Returns:
            Tuple of (leads, total_count)
        """
        query = """
        SELECT * FROM leads
        ORDER BY created_at DESC
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
        List leads by status.
        """
        query = """
        SELECT * FROM leads
        WHERE status = $1
        ORDER BY created_at DESC
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
        INSERT INTO call_sessions (lead_id, language_detected, conversation_history, duration_seconds, created_at)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING *
        """
        result = await self.db.execute_insert_returning(
            query,
            (str(lead_id), language_detected, json.dumps([]), 0, datetime.utcnow())
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
        duration_seconds: Optional[int] = None,
        classification: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Update call session.
        """
        updates = {}
        if conversation_history is not None:
            updates["conversation_history"] = json.dumps(conversation_history)
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
        (lead_id, call_session_id, interest_score, engagement_score, sentiment_score, composite_score, classification, timestamp)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING *
        """
        
        result = await self.db.execute_insert_returning(
            query,
            (
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
        INSERT INTO objections_log (call_session_id, objection_type, objection_text, resolved, timestamp)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING *
        """
        result = await self.db.execute_insert_returning(
            query,
            (str(call_session_id), objection_type, objection_text, False, datetime.utcnow())
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
        INSERT INTO documents (file_name, document_type, upload_user_id, chunk_count, uploaded_at)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING *
        """
        result = await self.db.execute_insert_returning(
            query,
            (file_name, document_type, upload_user_id, 0, datetime.utcnow())
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
        (document_id, content, embedding, language, objection_type, benefit_type, source_section, created_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING *
        """
        
        result = await self.db.execute_insert_returning(
            query,
            (
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
        INSERT INTO rm_assignments (lead_id, rm_name, assigned_at, converted)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (lead_id) DO UPDATE
        SET rm_name = $2, assigned_at = $3
        RETURNING *
        """
        result = await self.db.execute_insert_returning(
            query,
            (str(lead_id), rm_name, datetime.utcnow(), False)
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
