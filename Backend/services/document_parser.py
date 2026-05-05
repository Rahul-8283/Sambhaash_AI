"""
Document Parser Service
Handles PDF, DOCX, JSON, TXT file parsing and intelligent chunking
"""

from typing import List, Optional, Dict, Any
import logging
import json
from pathlib import Path
from io import BytesIO

logger = logging.getLogger(__name__)


class DocumentChunk:
    """Represents a chunk of parsed document content"""

    def __init__(
        self,
        text: str,
        chunk_id: int,
        source_section: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.text = text
        self.chunk_id = chunk_id
        self.source_section = source_section or "unknown"
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "chunk_id": self.chunk_id,
            "source_section": self.source_section,
            "metadata": self.metadata
        }


class DocumentParser:
    """
    Parse documents (PDF, DOCX, JSON, TXT) and chunk intelligently.
    """

    # Chunking parameters
    CHUNK_SIZE_TOKENS = 500  # ~375 words
    CHUNK_OVERLAP_TOKENS = 100  # ~75 words
    WORDS_PER_TOKEN = 0.75  # Rough approximation

    def __init__(self):
        """Initialize parser"""
        self.chunk_size_words = int(self.CHUNK_SIZE_TOKENS / self.WORDS_PER_TOKEN)
        self.chunk_overlap_words = int(self.CHUNK_OVERLAP_TOKENS / self.WORDS_PER_TOKEN)

    def parse_file(self, file_content: bytes, file_type: str) -> tuple[str, List[Dict[str, Any]]]:
        """
        Parse file and return (full_text, metadata_list)
        
        Args:
            file_content: Raw file bytes
            file_type: 'pdf', 'docx', 'json', 'txt'
        
        Returns:
            Tuple of (full_text, metadata_list)
        """
        file_type = file_type.lower()
        
        if file_type == "pdf":
            return self._parse_pdf(file_content)
        elif file_type == "docx":
            return self._parse_docx(file_content)
        elif file_type == "json":
            return self._parse_json(file_content)
        elif file_type == "txt":
            return self._parse_txt(file_content)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    def chunk_text(
        self,
        text: str,
        strategy: str = "semantic",
        section_name: Optional[str] = None
    ) -> List[DocumentChunk]:
        """
        Chunk text intelligently.
        
        Args:
            text: Full document text
            strategy: 'semantic' (at section boundaries) or 'sliding' (fixed size)
            section_name: Name of section for metadata
        
        Returns:
            List of DocumentChunk objects
        """
        if not text or not text.strip():
            return []

        if strategy == "semantic":
            return self._chunk_semantic(text, section_name)
        else:
            return self._chunk_sliding(text, section_name)

    def _parse_pdf(self, file_content: bytes) -> tuple[str, List[Dict[str, Any]]]:
        """Parse PDF file"""
        try:
            from PyPDF2 import PdfReader
            
            pdf = PdfReader(BytesIO(file_content))
            text_parts = []
            metadata_list = []
            
            for page_num, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text.strip():
                    text_parts.append(page_text)
                    metadata_list.append({
                        "page_number": page_num + 1,
                        "section_name": f"Page {page_num + 1}"
                    })
            
            full_text = "\n\n".join(text_parts)
            logger.info(f"[PARSER] PDF parsed: {len(text_parts)} pages, {len(full_text)} characters")
            
            return full_text, metadata_list
        except Exception as e:
            logger.error(f"[PARSER] PDF parse error: {e}")
            raise

    def _parse_docx(self, file_content: bytes) -> tuple[str, List[Dict[str, Any]]]:
        """Parse DOCX file"""
        try:
            from docx import Document
            
            doc = Document(BytesIO(file_content))
            text_parts = []
            metadata_list = []
            
            for para_num, paragraph in enumerate(doc.paragraphs):
                if paragraph.text.strip():
                    text_parts.append(paragraph.text)
                    style = paragraph.style.name if paragraph.style else "normal"
                    metadata_list.append({
                        "paragraph_number": para_num + 1,
                        "style": style,
                        "section_name": style
                    })
            
            full_text = "\n\n".join(text_parts)
            logger.info(f"[PARSER] DOCX parsed: {len(text_parts)} paragraphs, {len(full_text)} characters")
            
            return full_text, metadata_list
        except Exception as e:
            logger.error(f"[PARSER] DOCX parse error: {e}")
            raise

    def _parse_json(self, file_content: bytes) -> tuple[str, List[Dict[str, Any]]]:
        """Parse JSON file (flattened to text for chunking)"""
        try:
            data = json.loads(file_content.decode('utf-8'))
            
            # Flatten JSON to readable text
            text_parts = []
            metadata_list = []
            
            def flatten_dict(obj, prefix=""):
                parts = []
                meta = []
                
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        section_name = f"{prefix}.{key}" if prefix else key
                        
                        if isinstance(value, (dict, list)):
                            sub_parts, sub_meta = flatten_dict(value, section_name)
                            parts.extend(sub_parts)
                            meta.extend(sub_meta)
                        else:
                            text_line = f"{section_name}: {str(value)}"
                            parts.append(text_line)
                            meta.append({"section_name": section_name})
                
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        section_name = f"{prefix}[{i}]"
                        sub_parts, sub_meta = flatten_dict(item, section_name)
                        parts.extend(sub_parts)
                        meta.extend(sub_meta)
                
                else:
                    text_line = f"{prefix}: {str(obj)}"
                    parts.append(text_line)
                    meta.append({"section_name": prefix})
                
                return parts, meta
            
            text_parts, metadata_list = flatten_dict(data)
            full_text = "\n".join(text_parts)
            logger.info(f"[PARSER] JSON parsed: {len(text_parts)} items, {len(full_text)} characters")
            
            return full_text, metadata_list
        except Exception as e:
            logger.error(f"[PARSER] JSON parse error: {e}")
            raise

    def _parse_txt(self, file_content: bytes) -> tuple[str, List[Dict[str, Any]]]:
        """Parse TXT file"""
        try:
            text = file_content.decode('utf-8', errors='ignore')
            
            # Try to identify sections from headers (lines with ## or similar)
            lines = text.split('\n')
            metadata_list = []
            current_section = "document"
            
            for i, line in enumerate(lines):
                if line.strip().startswith('#'):
                    current_section = line.strip().lstrip('#').strip()
                
                metadata_list.append({
                    "line_number": i + 1,
                    "section_name": current_section
                })
            
            logger.info(f"[PARSER] TXT parsed: {len(lines)} lines, {len(text)} characters")
            return text, metadata_list
        except Exception as e:
            logger.error(f"[PARSER] TXT parse error: {e}")
            raise

    def _chunk_semantic(self, text: str, section_name: Optional[str] = None) -> List[DocumentChunk]:
        """
        Chunk at semantic boundaries (paragraphs, sections).
        Falls back to sliding window if no clear boundaries found.
        """
        # Split by double newlines (paragraphs)
        paragraphs = text.split('\n\n')
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        if not paragraphs:
            # Fallback to sliding window
            return self._chunk_sliding(text, section_name)
        
        chunks = []
        current_chunk = []
        current_size = 0
        chunk_id = 0
        
        for para in paragraphs:
            para_words = len(para.split())
            
            # If adding this paragraph would exceed chunk size, save current chunk
            if current_size + para_words > self.chunk_size_words and current_chunk:
                chunk_text = "\n\n".join(current_chunk)
                chunks.append(DocumentChunk(
                    text=chunk_text,
                    chunk_id=chunk_id,
                    source_section=section_name or "document",
                    metadata={"strategy": "semantic"}
                ))
                chunk_id += 1
                
                # Add overlap: keep last paragraph for context
                current_chunk = [current_chunk[-1], para] if len(current_chunk) > 0 else [para]
                current_size = len(" ".join(current_chunk).split())
            else:
                current_chunk.append(para)
                current_size += para_words
        
        # Add final chunk
        if current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            chunks.append(DocumentChunk(
                text=chunk_text,
                chunk_id=chunk_id,
                source_section=section_name or "document",
                metadata={"strategy": "semantic"}
            ))
        
        logger.info(f"[PARSER] Semantic chunking: {len(chunks)} chunks from {len(paragraphs)} paragraphs")
        return chunks

    def _chunk_sliding(self, text: str, section_name: Optional[str] = None) -> List[DocumentChunk]:
        """
        Chunk using sliding window of fixed size with overlap.
        """
        words = text.split()
        if not words:
            return []
        
        chunks = []
        chunk_id = 0
        
        for i in range(0, len(words), self.chunk_size_words - self.chunk_overlap_words):
            chunk_words = words[i:i + self.chunk_size_words]
            if chunk_words:
                chunk_text = " ".join(chunk_words)
                chunks.append(DocumentChunk(
                    text=chunk_text,
                    chunk_id=chunk_id,
                    source_section=section_name or "document",
                    metadata={"strategy": "sliding"}
                ))
                chunk_id += 1
        
        logger.info(f"[PARSER] Sliding window chunking: {len(chunks)} chunks")
        return chunks
