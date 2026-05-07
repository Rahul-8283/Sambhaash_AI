# services/llm/embedder.py
"""
Lightweight Cloud Embedding Service (0MB Local RAM!)
Uses Hugging Face Free Inference API to extract 384-dimensional vectors 
for both development and production. This eliminates local PyTorch and 
sentence-transformers completely, dropping local RAM usage to almost 0MB!
"""

import os
import logging
from typing import List, Optional, Tuple
import numpy as np
from huggingface_hub import InferenceClient
from config import get_config

logger = logging.getLogger(__name__)


class EmbedderService:
    """
    Lightweight embedding service that uses Hugging Face cloud endpoints
    for both development and production to completely avoid local PyTorch RAM usage.
    """

    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIM = 384

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize embedder.
        """
        self.model_name = model_name or self.MODEL_NAME
        # We always use the Cloud API to save local RAM and disk space
        self.use_cloud = True
        self.model = None
        
        logger.info(f"[EMBEDDER] Initialized — using Hugging Face Cloud Inference API for 384-dim embeddings ({self.model_name})")
        # Grab Hugging Face API key/token from central config
        self.settings = get_config()
        self.hf_token = self.settings.hf_api_key
        
        # Initialize official Hugging Face Inference Client
        self.client = InferenceClient(api_key=self.hf_token)

    def get_embedding_dimension(self) -> int:
        """Get embedding vector dimension"""
        return self.EMBEDDING_DIM

    def embed_text(self, text: str, normalize: bool = True) -> List[float]:
        """
        Convert single text to embedding vector.
        """
        if not text or not isinstance(text, str):
            logger.warning("[EMBEDDER] Invalid text input")
            return [0.0] * self.EMBEDDING_DIM

        try:
            emb = self.client.feature_extraction(
                model=self.model_name,
                text=text
            )
            # The client returns a numpy array. Let's process it
            vector = emb.tolist() if hasattr(emb, "tolist") else list(emb)
            
            # If it's a 2D or 3D list (e.g. [[val, val, ...]]), mean-pool or extract the sentence embedding
            if isinstance(vector, list) and len(vector) > 0 and isinstance(vector[0], list):
                vector_arr = np.array(vector)
                if len(vector_arr.shape) > 1:
                    vector = np.mean(vector_arr, axis=0).tolist()
            
            if len(vector) == self.EMBEDDING_DIM:
                if normalize:
                    vec_arr = np.array(vector)
                    norm = np.linalg.norm(vec_arr)
                    if norm > 0:
                        vector = (vec_arr / norm).tolist()
                return vector
            else:
                # Padding or truncating to expected size
                if len(vector) < self.EMBEDDING_DIM:
                    return vector + [0.0] * (self.EMBEDDING_DIM - len(vector))
                return vector[:self.EMBEDDING_DIM]
        except Exception as e:
            logger.error(f"[EMBEDDER] Cloud encoding failed: {e}")
            
        # Safety fallback to prevent crashes on API outages
        return [0.0] * self.EMBEDDING_DIM

    def embed_texts(self, texts: List[str], normalize: bool = True, batch_size: int = 32) -> List[List[float]]:
        """
        Convert multiple texts to embedding vectors.
        """
        if not texts:
            logger.warning("[EMBEDDER] Empty text list provided")
            return []

        try:
            # huggingface_hub client.feature_extraction natively supports list of inputs and handles batches!
            embs = self.client.feature_extraction(
                model=self.model_name,
                text=texts
            )
            # Process result array
            embs_arr = np.array(embs)
            
            all_embeddings = []
            for i, emb in enumerate(embs_arr):
                vector = emb.tolist() if hasattr(emb, "tolist") else list(emb)
                if len(vector) == self.EMBEDDING_DIM:
                    if normalize:
                        vec_arr = np.array(vector)
                        norm = np.linalg.norm(vec_arr)
                        if norm > 0:
                            vector = (vec_arr / norm).tolist()
                    all_embeddings.append(vector)
                else:
                    if len(vector) < self.EMBEDDING_DIM:
                        vector = vector + [0.0] * (self.EMBEDDING_DIM - len(vector))
                    else:
                        vector = vector[:self.EMBEDDING_DIM]
                    all_embeddings.append(vector)
            return all_embeddings
        except Exception as e:
            logger.error(f"[EMBEDDER] Cloud batch encoding failed: {e}")
            
        # Fallback to zero vectors in case of exception
        return [[0.0] * self.EMBEDDING_DIM for _ in texts]

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