# services/llm/embedder.py
"""
Local Embedding Service using sentence-transformers
No API key required — uses free, local all-MiniLM-L6-v2 model
384-dimensional vectors optimized for semantic similarity
"""

from typing import List, Optional, Tuple
import logging
import numpy as np
from sentence_transformers import SentenceTransformer, util

logger = logging.getLogger(__name__)


class EmbedderService:
    """
    Local embedding service using sentence-transformers.
    Converts text to 384-dimensional vectors for pgvector storage.
    """

    MODEL_NAME = "all-MiniLM-L6-v2"
    EMBEDDING_DIM = 384

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize embedder with local model.
        
        Args:
            model_name: Optional model name. Defaults to all-MiniLM-L6-v2
        """
        self.model_name = model_name or self.MODEL_NAME
        try:
            logger.info(f"[EMBEDDER] Loading model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"[EMBEDDER] Model loaded successfully. Dimension: {self.get_embedding_dimension()}")
        except Exception as e:
            logger.error(f"[EMBEDDER] Failed to load model: {e}")
            raise

    def get_embedding_dimension(self) -> int:
        """Get embedding vector dimension"""
        return self.EMBEDDING_DIM

    def embed_text(self, text: str, normalize: bool = True) -> List[float]:
        """
        Convert single text to embedding vector.

        Args:
            text: Text to embed
            normalize: Whether to normalize vector (L2 norm)

        Returns:
            384-dimensional embedding vector
        """
        if not text or not isinstance(text, str):
            logger.warning("[EMBEDDER] Invalid text input")
            return [0.0] * self.EMBEDDING_DIM

        try:
            embedding = self.model.encode(
                text,
                convert_to_numpy=True,
                normalize_embeddings=normalize
            )
            return embedding.tolist()
        except Exception as e:
            logger.error(f"[EMBEDDER] Error embedding text: {e}")
            return [0.0] * self.EMBEDDING_DIM

    def embed_texts(self, texts: List[str], normalize: bool = True, batch_size: int = 32) -> List[List[float]]:
        """
        Convert multiple texts to embedding vectors (batch processing).

        Args:
            texts: List of texts to embed
            normalize: Whether to normalize vectors
            batch_size: Batch size for efficient processing

        Returns:
            List of 384-dimensional embedding vectors
        """
        if not texts:
            logger.warning("[EMBEDDER] Empty text list provided")
            return []

        try:
            logger.debug(f"[EMBEDDER] Embedding batch of {len(texts)} texts")
            embeddings = self.model.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=normalize,
                batch_size=batch_size,
                show_progress_bar=False
            )
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"[EMBEDDER] Error embedding batch: {e}")
            return [[0.0] * self.EMBEDDING_DIM for _ in texts]

    def similarity(
        self,
        query_embedding: List[float],
        document_embeddings: List[List[float]],
        top_k: Optional[int] = None
    ) -> List[Tuple[int, float]]:
        """
        Compute cosine similarity between query and documents.

        Args:
            query_embedding: Query embedding vector
            document_embeddings: List of document embeddings
            top_k: Return only top-k results

        Returns:
            List of (index, similarity_score) tuples sorted by similarity
        """
        if not document_embeddings:
            return []

        try:
            query_emb = np.array(query_embedding)
            doc_embs = np.array(document_embeddings)

            # Compute cosine similarity
            similarities = util.cos_sim(query_emb, doc_embs)[0].numpy()

            # Get indices sorted by similarity (descending)
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

        Args:
            query: Search query
            corpus: List of candidate texts
            top_k: Number of top results

        Returns:
            List of dicts with 'index', 'corpus_id', 'score', 'text'
        """
        if not corpus:
            logger.warning("[EMBEDDER] Empty corpus provided")
            return []

        try:
            # Embed query and corpus
            query_emb = self.model.encode(query, convert_to_numpy=True, normalize_embeddings=True)
            corpus_embs = self.model.encode(
                corpus,
                convert_to_numpy=True,
                normalize_embeddings=True,
                batch_size=32
            )

            # Find top-k matches
            hits = util.semantic_search(query_emb, corpus_embs, top_k=min(top_k, len(corpus)))

            results = []
            for hit in hits[0]:  # semantic_search returns list of lists
                idx = hit['corpus_id']
                results.append({
                    'index': idx,
                    'corpus_id': idx,
                    'score': float(hit['score']),
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
            "max_seq_length": self.model.get_max_seq_length(),
            "device": str(self.model.device)
        }


# Backward compatibility: Keep TextEmbedder as alias
class TextEmbedder(EmbedderService):
    """Backward compatible alias for EmbedderService"""
    
    def embed_batch(self, texts: List[str], normalize: bool = True, batch_size: int = 32) -> List[List[float]]:
        """Alias for embed_texts for backward compatibility"""
        return self.embed_texts(texts, normalize=normalize, batch_size=batch_size)