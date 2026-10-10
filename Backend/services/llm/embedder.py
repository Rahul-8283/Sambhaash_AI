# services/llm/embedder.py
"""
Local embedding service.

Runs sentence-transformers/all-MiniLM-L6-v2 (384-dim) through fastembed's ONNX
runtime: no API key, no network call per query, no PyTorch. The vectors are the
same ones the Hugging Face Inference API produced, so chunks embedded earlier
stay searchable (cosine similarity of old vs new vectors is 1.0).
"""

import logging
import threading
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

from config import get_config

logger = logging.getLogger(__name__)


class EmbeddingError(RuntimeError):
    """The embedding backend failed (model unavailable, bad input, ...)."""


# One model per process, shared by every EmbedderService instance
_model = None
_model_lock = threading.Lock()


def _load_model(model_name: str):
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is None:
            from fastembed import TextEmbedding

            cache_dir = get_config().embedding_cache_dir
            Path(cache_dir).mkdir(parents=True, exist_ok=True)
            logger.info(f"[EMBEDDER] Loading {model_name} (cache: {cache_dir})")
            _model = TextEmbedding(model_name=model_name, cache_dir=cache_dir)
            logger.info("[EMBEDDER] Model ready")
    return _model


class EmbedderService:
    """Embeds text into normalized 384-dimensional vectors, locally."""

    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIM = 384

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or self.MODEL_NAME

    def warm_up(self) -> None:
        """Load the model now so the first live call does not pay for it."""
        _load_model(self.model_name)

    def get_embedding_dimension(self) -> int:
        return self.EMBEDDING_DIM

    def _embed(self, texts: List[str], normalize: bool) -> List[List[float]]:
        try:
            model = _load_model(self.model_name)
            vectors = [np.asarray(v, dtype=float) for v in model.embed(texts)]
        except Exception as e:
            # Never hand back a zero vector: it scores 0 against everything, so a
            # broken backend would look like "no relevant knowledge" and, on
            # upload, would store unsearchable chunks.
            logger.error(f"[EMBEDDER] Encoding failed: {e}")
            raise EmbeddingError(f"Embedding failed: {e}") from e

        result = []
        for vec in vectors:
            if vec.shape[0] != self.EMBEDDING_DIM:
                raise EmbeddingError(
                    f"Model returned {vec.shape[0]} dimensions, expected {self.EMBEDDING_DIM}"
                )
            if normalize:
                norm = np.linalg.norm(vec)
                if norm > 0:
                    vec = vec / norm
            result.append(vec.tolist())
        return result

    def embed_text(self, text: str, normalize: bool = True) -> List[float]:
        """Embed one text. Raises ValueError on empty input, EmbeddingError on failure."""
        if not text or not isinstance(text, str):
            raise ValueError("embed_text needs a non-empty string")
        return self._embed([text], normalize)[0]

    def embed_texts(self, texts: List[str], normalize: bool = True, batch_size: int = 32) -> List[List[float]]:
        """Embed many texts (order preserved). Raises EmbeddingError on failure."""
        if not texts:
            return []
        return self._embed(list(texts), normalize)

    def similarity(
        self,
        query_embedding: List[float],
        document_embeddings: List[List[float]],
        top_k: Optional[int] = None
    ) -> List[Tuple[int, float]]:
        """
        Compute cosine similarity between query and documents using NumPy.
        """
        if not document_embeddings:
            return []

        try:
            q = np.array(query_embedding)
            d = np.array(document_embeddings)

            # Cosine similarity formula via NumPy
            q_norm = np.linalg.norm(q)
            if q_norm == 0:
                similarities = np.zeros(len(d))
            else:
                d_norms = np.linalg.norm(d, axis=1)
                d_norms[d_norms == 0] = 1.0  # Avoid division by zero
                similarities = np.dot(d, q) / (q_norm * d_norms)

            sorted_indices = np.argsort(-similarities)
            if top_k:
                sorted_indices = sorted_indices[:top_k]

            results = [
                (int(idx), float(similarities[idx]))
                for idx in sorted_indices
            ]
            return results
        except Exception as e:
            logger.error(f"[EMBEDDER] Error computing similarity: {e}")
            return []

    def semantic_search(
        self,
        query: str,
        corpus: List[str],
        top_k: int = 5
    ) -> List[dict]:
        """
        Semantic search: find most relevant corpus texts for query.
        """
        if not corpus:
            logger.warning("[EMBEDDER] Empty corpus provided")
            return []

        try:
            query_emb = self.embed_text(query, normalize=True)
            corpus_embs = self.embed_texts(corpus, normalize=True, batch_size=32)

            similarities = self.similarity(query_emb, corpus_embs, top_k=top_k)

            results = []
            for idx, score in similarities:
                results.append({
                    'index': idx,
                    'corpus_id': idx,
                    'score': score,
                    'text': corpus[idx]
                })
            return results
        except Exception as e:
            logger.error(f"[EMBEDDER] Error in semantic search: {e}")
            return []

    def get_model_info(self) -> dict:
        """Get information about loaded model"""
        return {
            "model_name": self.model_name,
            "embedding_dimension": self.EMBEDDING_DIM,
            "max_seq_length": 512,
            "device": "cloud-api"
        }


# Backward compatibility: Keep TextEmbedder as alias
class TextEmbedder(EmbedderService):
    """Backward compatible alias for EmbedderService"""
    
    def embed_batch(self, texts: List[str], normalize: bool = True, batch_size: int = 32) -> List[List[float]]:
        """Alias for embed_texts for backward compatibility"""
        return self.embed_texts(texts, normalize=normalize, batch_size=batch_size)