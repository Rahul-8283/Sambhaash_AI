"""
SQLAlchemy ORM Models for Sambhaash AI Database

Tables:
- leads
- call_sessions
- lead_scores
- objections_log
- documents
- knowledge_base
- rm_assignments
"""

from sqlalchemy import (
    Column, String, Float, Integer, Boolean, DateTime, JSON, Text, ForeignKey,
    Index, Enum as SQLEnum, func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from enum import Enum as PyEnum

Base = declarative_base()


class LeadStatus(str, PyEnum):
    """Lead status enumeration"""
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    INTERESTED = "INTERESTED"
    CONVERTED = "CONVERTED"
    REJECTED = "REJECTED"
    FOLLOW_UP = "FOLLOW_UP"


class LeadClassification(str, PyEnum):
    """Lead quality classification"""
    HOT = "HOT"
    WARM = "WARM"
    COLD = "COLD"


class ConversationClassification(str, PyEnum):
    """Conversation classification"""
    OBJECTION = "OBJECTION"
    BENEFIT = "BENEFIT"
    FAQ = "FAQ"
    GENERIC = "GENERIC"


class DocumentType(str, PyEnum):
    """Document type enumeration"""
    PDF = "PDF"
    DOCX = "DOCX"
    JSON = "JSON"
    TXT = "TXT"


# ==================== MODELS ====================

class Lead(Base):
    """
    Lead information and contact details
    """
    __tablename__ = "leads"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone = Column(String(20), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True, index=True)
    language = Column(String(50), nullable=False, default="hi")
    status = Column(SQLEnum(LeadStatus), nullable=False, default=LeadStatus.NEW, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    call_sessions = relationship("CallSession", back_populates="lead", cascade="all, delete-orphan")
    lead_scores = relationship("LeadScore", back_populates="lead", cascade="all, delete-orphan")
    rm_assignments = relationship("RmAssignment", back_populates="lead", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Lead {self.phone} ({self.status})>"


class CallSession(Base):
    """
    Individual call session with conversation history and KB context tracking
    """
    __tablename__ = "call_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_history = Column(JSON, nullable=False, default=list)
    kb_usage_log = Column(JSON, nullable=False, default=list)  # Track KB articles used per turn
    classification = Column(
        SQLEnum(ConversationClassification),
        nullable=True,
        index=True
    )
    language_detected = Column(String(50), nullable=True)
    duration_seconds = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    
    # Relationships
    lead = relationship("Lead", back_populates="call_sessions")
    lead_scores = relationship("LeadScore", back_populates="call_session", cascade="all, delete-orphan")
    objections_log = relationship("ObjectionLog", back_populates="call_session", cascade="all, delete-orphan")
    
    # Index for faster queries
    __table_args__ = (
        Index("ix_call_sessions_lead_created", "lead_id", "created_at"),
    )
    
    def __repr__(self):
        return f"<CallSession {self.id} lead={self.lead_id}>"


class LeadScore(Base):
    """
    Lead scoring results from individual calls
    """
    __tablename__ = "lead_scores"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    call_session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("call_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    interest_score = Column(Float, nullable=False, default=0.0)
    engagement_score = Column(Float, nullable=False, default=0.0)
    sentiment_score = Column(Float, nullable=False, default=0.0)
    composite_score = Column(Float, nullable=False, default=0.0)
    classification = Column(
        SQLEnum(LeadClassification),
        nullable=False,
        index=True
    )
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    
    # Relationships
    lead = relationship("Lead", back_populates="lead_scores")
    call_session = relationship("CallSession", back_populates="lead_scores")
    
    # Index for latest score queries (composite index)
    __table_args__ = (
        Index("ix_lead_scores_lead_timestamp", "lead_id", "timestamp"),
    )
    
    def __repr__(self):
        return f"<LeadScore lead={self.lead_id} score={self.composite_score:.2f} class={self.classification}>"


class ObjectionLog(Base):
    """
    Log of objections raised during calls
    """
    __tablename__ = "objections_log"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("call_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    objection_type = Column(String(100), nullable=True, index=True)
    objection_text = Column(Text, nullable=True)
    resolved = Column(Boolean, nullable=False, default=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    
    # Relationships
    call_session = relationship("CallSession", back_populates="objections_log")
    
    def __repr__(self):
        return f"<ObjectionLog type={self.objection_type} resolved={self.resolved}>"


class Document(Base):
    """
    Uploaded documents for knowledge base (Appendix A)
    """
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    upload_user_id = Column(String(255), nullable=True)
    document_type = Column(SQLEnum(DocumentType), nullable=False)
    file_name = Column(String(500), nullable=False)
    chunk_count = Column(Integer, nullable=False, default=0)
    uploaded_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    
    # Relationships
    knowledge_base_entries = relationship("KnowledgeBase", back_populates="document", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Document {self.file_name} ({self.document_type})>"


class KnowledgeBase(Base):
    """
    Knowledge base entries with vector embeddings (pgvector)
    Used for RAG retrieval during calls
    """
    __tablename__ = "knowledge_base"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    content = Column(Text, nullable=False)
    embedding = Column(String(None), nullable=True)  # pgvector stored as text/JSON in asyncpg
    language = Column(String(50), nullable=False, default="hi", index=True)
    objection_type = Column(String(100), nullable=True, index=True)
    benefit_type = Column(String(100), nullable=True, index=True)
    source_section = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    
    # Relationships
    document = relationship("Document", back_populates="knowledge_base_entries")
    
    def __repr__(self):
        return f"<KnowledgeBase {self.id[:8]}... lang={self.language}>"


class RmAssignment(Base):
    """
    RM (Relationship Manager) assignments for HOT leads
    """
    __tablename__ = "rm_assignments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id = Column(
        UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    rm_name = Column(String(255), nullable=False, index=True)
    assigned_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    converted = Column(Boolean, nullable=False, default=False, index=True)
    
    # Relationships
    lead = relationship("Lead", back_populates="rm_assignments")
    
    def __repr__(self):
        return f"<RmAssignment lead={self.lead_id} rm={self.rm_name}>"


class CallRecording(Base):
    """
    Call recordings and transcriptions (Phase 2B)
    Stores audio file metadata and transcription text
    """
    __tablename__ = "call_recordings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("call_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True
    )
    # Twilio recording metadata
    twilio_recording_sid = Column(String(255), nullable=True, index=True)
    twilio_call_sid = Column(String(255), nullable=True, index=True)
    
    # Storage paths
    storage_path = Column(String(512), nullable=False)  # e.g., "recordings/2026-05-05_123456_abc123.wav"
    storage_url = Column(String(512), nullable=True)    # Public URL to recording
    
    # Recording metadata
    duration_seconds = Column(Integer, nullable=False, default=0)
    file_size_bytes = Column(Integer, nullable=False, default=0)
    
    # Transcription data
    transcription_text = Column(Text, nullable=True)    # Full transcription from Whisper
    transcription_language = Column(String(50), nullable=True)
    transcription_confidence = Column(Float, nullable=True)  # Whisper confidence score
    
    # Summary & analytics
    call_summary = Column(Text, nullable=True)          # AI-generated summary of call
    key_topics = Column(JSON, nullable=False, default=list)  # ["product", "pricing", "demo"]
    sentiment = Column(String(20), nullable=True)       # positive, negative, neutral
    
    # Timestamps
    recorded_at = Column(DateTime(timezone=True), nullable=False)  # When call happened
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    
    # Relationships
    call_session = relationship("CallSession", backref="recordings")
    
    # Index for faster queries
    __table_args__ = (
        Index("ix_call_recordings_session_created", "call_session_id", "created_at"),
        Index("ix_call_recordings_language", "transcription_language"),
    )
    
    def __repr__(self):
        return f"<CallRecording session={self.call_session_id} duration={self.duration_seconds}s>"
