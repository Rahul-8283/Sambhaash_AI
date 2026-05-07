"""
Admin Routes - Knowledge Base Management
Handles document upload, embedding generation, and KB operations
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
import logging
import io
from datetime import datetime

from services.database.supabase_client import get_db_client, SupabaseClient
from services.database.repository import Repository
from services.document_parser import DocumentParser, DocumentChunk
from services.llm.embedder import EmbedderService
from services.storage_client import get_storage_client, SupabaseStorageClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/kb", tags=["admin-kb"])

# ==================== PYDANTIC MODELS ====================


class DocumentUploadResponse(BaseModel):
    """Response for document upload"""
    status: str = Field(..., description="Status: 'indexed' or 'error'")
    document_id: str = Field(..., description="Document ID in database")
    file_name: str = Field(..., description="Uploaded file name")
    chunks_created: int = Field(..., description="Number of chunks created")
    storage_path: str = Field(..., description="File path in Supabase Storage")
    storage_url: str = Field(..., description="Public URL in Supabase Storage")
    message: str = Field(..., description="Status message")


class KnowledgeBaseChunk(BaseModel):
    """Knowledge base chunk information"""
    chunk_id: str
    document_id: str
    text: str
    language: str
    source_section: Optional[str]
    objection_type: Optional[str]
    similarity_score: Optional[float] = None


class DocumentInfo(BaseModel):
    """Document information"""
    document_id: str
    file_name: str
    document_type: str
    chunk_count: int
    uploaded_at: str


class KBStatsResponse(BaseModel):
    """Knowledge base statistics"""
    total_chunks: int = Field(..., description="Total KB entries")
    total_documents: int = Field(..., description="Total uploaded documents")
    languages: List[Dict[str, Any]] = Field(..., description="Language distribution")


class KBSearchResponse(BaseModel):
    """Search results from KB"""
    query: str
    top_k: int
    results: List[KnowledgeBaseChunk]
    total_found: int


# ==================== GLOBAL SERVICE INSTANCES ====================

# Lazy initialization of services
_embedder_service: Optional[EmbedderService] = None
_document_parser: Optional[DocumentParser] = None


async def get_embedder() -> EmbedderService:
    """Get or initialize embedder service (lazy loading)"""
    global _embedder_service
    if _embedder_service is None:
        logger.info("[ADMIN] Initializing embedder service...")
        _embedder_service = EmbedderService()
    return _embedder_service


async def get_parser() -> DocumentParser:
    """Get or initialize document parser (lazy loading)"""
    global _document_parser
    if _document_parser is None:
        logger.info("[ADMIN] Initializing document parser...")
        _document_parser = DocumentParser()
    return _document_parser


# ==================== ROUTES ====================


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=201,
    summary="Upload and index Appendix A or knowledge documents"
)
async def upload_knowledge_base(
    file: UploadFile = File(..., description="PDF, DOCX, JSON, or TXT file"),
    doc_type: str = Query(default="appendix_a", description="Document type: appendix_a, faq, script, policy"),
    language: str = Query(default="hi", description="Language: hi, en, tamil, telugu, etc."),
    db: SupabaseClient = Depends(get_db_client),
    storage: SupabaseStorageClient = Depends(get_storage_client),
    embedder: EmbedderService = Depends(get_embedder),
    parser: DocumentParser = Depends(get_parser),
) -> DocumentUploadResponse:
    """
    Upload and index a knowledge document.
    
    Process:
    1. Save file to Supabase Storage
    2. Parse file → extract text
    3. Chunk intelligently → 500 tokens per chunk
    4. Generate embeddings → 384-dimensional vectors
    5. Store in pgvector → ready for RAG retrieval
    
    Supported formats:
    - PDF (text extraction)
    - DOCX (paragraph extraction)
    - JSON (flattened structure)
    - TXT (line-based)
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="File name is required")
        
        # Detect file type from extension
        file_ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        if file_ext not in ["pdf", "docx", "json", "txt"]:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_ext}")
        
        logger.info(f"[ADMIN] Uploading: {file.filename} (type: {file_ext}, doc_type: {doc_type})")
        
        # Read file content
        file_content = await file.read()
        if not file_content:
            raise HTTPException(status_code=400, detail="File is empty")
        
        # ==================== STEP 1: SAVE TO STORAGE ====================
        
        # Generate storage path: documents/{timestamp}_{filename}
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        storage_path = f"documents/{timestamp}_{file.filename}"
        
        # Determine content type
        content_type_map = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "json": "application/json",
            "txt": "text/plain"
        }
        content_type = content_type_map.get(file_ext, "application/octet-stream")
        
        logger.info(f"[ADMIN] Saving to storage: {storage_path}")
        
        # Upload to Supabase Storage
        storage_result = await storage.upload_file(
            file_path=storage_path,
            file_content=file_content,
            content_type=content_type
        )
        
        storage_url = storage_result["public_url"]
        logger.info(f"[ADMIN] Storage URL: {storage_url}")
        
        # ==================== STEP 2: PARSE DOCUMENT ====================
        
        full_text, metadata_list = parser.parse_file(file_content, file_ext)
        if not full_text.strip():
            raise HTTPException(status_code=400, detail="No text extracted from file")
        
        logger.info(f"[ADMIN] Parsed {file.filename}: {len(full_text)} characters")
        
        # ==================== STEP 3: CHUNK DOCUMENT ====================
        
        chunks: List[DocumentChunk] = parser.chunk_text(
            full_text,
            strategy="semantic",
            section_name=doc_type
        )
        
        if not chunks:
            raise HTTPException(status_code=400, detail="Failed to chunk document")
        
        logger.info(f"[ADMIN] Created {len(chunks)} chunks from {file.filename}")
        
        # ==================== STEP 4: CREATE DATABASE RECORD ====================
        
        repo = Repository(db)
        doc_record = await repo.create_document(
            file_name=file.filename,
            document_type=file_ext.upper(),
            upload_user_id="admin"
        )
        document_id = UUID(str(doc_record["id"]))
        
        # ==================== STEP 5: GENERATE EMBEDDINGS ====================
        
        chunk_texts = [chunk.text for chunk in chunks]
        embeddings = embedder.embed_texts(chunk_texts, batch_size=32)
        
        logger.info(f"[ADMIN] Generated {len(embeddings)} embeddings")
        
        # ==================== STEP 6: STORE IN KNOWLEDGE BASE ====================
        
        stored_count = 0
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            try:
                await repo.insert_kb_entry(
                    document_id=document_id,
                    content=chunk.text,
                    embedding=embedding,
                    language=language,
                    objection_type=chunk.metadata.get("objection_tag"),
                    benefit_type=chunk.metadata.get("benefit_type"),
                    source_section=chunk.source_section
                )
                stored_count += 1
            except Exception as e:
                logger.error(f"[ADMIN] Error storing KB entry {i}: {e}")
                continue
        
        logger.info(f"[ADMIN] Successfully stored {stored_count}/{len(chunks)} chunks")
        
        return DocumentUploadResponse(
            status="indexed",
            document_id=str(document_id),
            file_name=file.filename,
            chunks_created=stored_count,
            storage_path=storage_path,
            storage_url=storage_url,
            message=f"Document uploaded and indexed successfully. {stored_count} chunks ready for RAG retrieval."
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ADMIN] Upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get(
    "/documents",
    response_model=List[DocumentInfo],
    summary="List all uploaded knowledge documents"
)
async def list_knowledge_documents(
    db: SupabaseClient = Depends(get_db_client),
) -> List[DocumentInfo]:
    """Get list of all uploaded documents with chunk counts."""
    try:
        repo = Repository(db)
        documents = await repo.list_documents()
        
        results = [
            DocumentInfo(
                document_id=str(doc["id"]),
                file_name=doc["file_name"],
                document_type=doc["document_type"],
                chunk_count=doc.get("chunk_count", 0),
                uploaded_at=str(doc.get("uploaded_at", ""))
            )
            for doc in documents
        ]
        
        logger.info(f"[ADMIN] Listed {len(results)} documents")
        return results
    except Exception as e:
        logger.error(f"[ADMIN] List error: {e}")
        raise HTTPException(status_code=500, detail="Failed to list documents")


@router.get(
    "/documents/{doc_id}",
    response_model=Dict[str, Any],
    summary="Get document details with chunks"
)
async def get_document_details(
    doc_id: str,
    db: SupabaseClient = Depends(get_db_client),
    limit: int = Query(10, ge=1, le=100, description="Max chunks to return")
) -> Dict[str, Any]:
    """Get document details and sample chunks."""
    try:
        repo = Repository(db)
        
        # Get document info
        query = "SELECT * FROM documents WHERE id = $1"
        doc = await repo.db.execute_fetchone(query, (doc_id,))
        
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Get sample chunks
        kb_query = """
        SELECT id, document_id, content, language, objection_type, source_section
        FROM knowledge_base
        WHERE document_id = $1
        LIMIT $2
        """
        chunks = await repo.db.execute_query(kb_query, (doc_id, limit))
        
        logger.info(f"[ADMIN] Retrieved details for document {doc_id}")
        
        return {
            "document": {
                "id": str(doc["id"]),
                "file_name": doc["file_name"],
                "document_type": doc["document_type"],
                "chunk_count": doc.get("chunk_count", 0),
                "uploaded_at": str(doc.get("uploaded_at", ""))
            },
            "sample_chunks": [
                {
                    "chunk_id": str(c["id"]),
                    "text": c.get("content", "")[:200] + "...",
                    "language": c.get("language"),
                    "section": c.get("source_section")
                }
                for c in chunks
            ],
            "total_samples": len(chunks)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ADMIN] Get details error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get document details")


@router.delete(
    "/documents/{doc_id}",
    response_model=Dict[str, str],
    summary="Delete a document and all its chunks"
)
async def delete_knowledge_document(
    doc_id: str,
    db: SupabaseClient = Depends(get_db_client),
) -> Dict[str, str]:
    """Delete a document and all associated KB chunks."""
    try:
        repo = Repository(db)
        
        # Verify document exists
        query = "SELECT * FROM documents WHERE id = $1"
        doc = await repo.db.execute_fetchone(query, (doc_id,))
        
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Delete KB entries (cascades due to foreign key)
        delete_query = "DELETE FROM documents WHERE id = $1"
        await repo.db.execute_update(delete_query, (doc_id,))
        
        logger.info(f"[ADMIN] Deleted document: {doc_id}")
        
        return {"status": "deleted", "document_id": doc_id, "message": f"Document {doc['file_name']} deleted with all chunks"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ADMIN] Delete error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete document")


@router.get(
    "/search",
    response_model=KBSearchResponse,
    summary="Search knowledge base by text query"
)
async def search_knowledge_base(
    query: str = Query(..., min_length=1, description="Search query text"),
    top_k: int = Query(5, ge=1, le=20, description="Number of results"),
    language: Optional[str] = Query(None, description="Filter by language"),
    objection_type: Optional[str] = Query(None, description="Filter by objection type"),
    db: SupabaseClient = Depends(get_db_client),
    embedder: EmbedderService = Depends(get_embedder),
) -> KBSearchResponse:
    """
    Search knowledge base using semantic similarity.
    
    Process:
    1. Embed query text → 384-dimensional vector
    2. Search pgvector for similar chunks
    3. Return ranked results with similarity scores
    """
    try:
        logger.info(f"[ADMIN] KB search: query='{query}' top_k={top_k}")
        
        # Generate query embedding
        query_embedding = embedder.embed_text(query)
        
        # Search repository
        repo = Repository(db)
        results = await repo.vector_search_knowledge_base(
            query_embedding=query_embedding,
            top_k=top_k,
            language=language,
            objection_type=objection_type
        )
        
        # Format results
        formatted_results = [
            KnowledgeBaseChunk(
                chunk_id=str(r.get("id", "")),
                document_id=str(r.get("document_id", "")),
                text=r.get("text", "")[:300],  # Truncate for response
                language=r.get("language", ""),
                source_section=r.get("source_section"),
                objection_type=r.get("objection_type"),
                similarity_score=float(r.get("score", 0.0))
            )
            for r in results
        ]
        
        logger.info(f"[ADMIN] Found {len(formatted_results)} results")
        
        return KBSearchResponse(
            query=query,
            top_k=top_k,
            results=formatted_results,
            total_found=len(formatted_results)
        )
    except Exception as e:
        logger.error(f"[ADMIN] Search error: {e}")
        raise HTTPException(status_code=500, detail="Search failed")


@router.get(
    "/stats",
    response_model=KBStatsResponse,
    summary="Get knowledge base statistics"
)
async def get_kb_statistics(
    db: SupabaseClient = Depends(get_db_client),
) -> KBStatsResponse:
    """Get overall knowledge base statistics and coverage."""
    try:
        repo = Repository(db)
        stats = await repo.get_knowledge_base_stats()
        
        logger.info(f"[ADMIN] KB stats retrieved")
        
        return KBStatsResponse(
            total_chunks=stats.get("total_chunks", 0),
            total_documents=stats.get("total_documents", 0),
            languages=stats.get("languages", [])
        )
    except Exception as e:
        logger.error(f"[ADMIN] Stats error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")
