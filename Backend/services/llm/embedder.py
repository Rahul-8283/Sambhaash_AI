# services/llm/embedder.py

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Dict, List, Optional, Sequence
from urllib import error, request


class EmbedderError(RuntimeError):
    pass


class TextEmbedder:
    """
    Embedding client for Appendix A / FAQ / script ingestion and retrieval.

    Supports:
    - OpenAI-compatible embeddings endpoint
    - deterministic local fallback when explicitly allowed
    """

    def __init__(
        self,
        model_name: str = "model name",
        api_key: str = "your api key",
        base_url: str = "https://api.openai.com/v1",
        timeout: int = 30,
        extra_headers: Optional[Dict[str, str]] = None,
        use_local_fallback: bool = True,
        local_dimension: int = 384,
    ) -> None:
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.extra_headers = extra_headers or {}
        self.use_local_fallback = use_local_fallback
        self.local_dimension = max(64, local_dimension)

    def embed_text(self, text: str) -> List[float]:
        text = (text or "").strip()
        if not text:
            return self._zero_vector()

        if self._is_configured():
            try:
                return self._remote_embed([text])[0]
            except Exception:
                if not self.use_local_fallback:
                    raise
        return self._local_embed(text)

    def embed_texts(self, texts: Sequence[str]) -> List[List[float]]:
        cleaned = [(t or "").strip() for t in texts]
        cleaned = [t for t in cleaned if t]

        if not cleaned:
            return []

        if self._is_configured():
            try:
                return self._remote_embed(cleaned)
            except Exception:
                if not self.use_local_fallback:
                    raise

        return [self._local_embed(text) for text in cleaned]

    def _remote_embed(self, texts: Sequence[str]) -> List[List[float]]:
        if not self.api_key or self.api_key.strip() == "your api key":
            raise EmbedderError("Embedder api_key is not configured.")

        url = f"{self.base_url}/embeddings"
        payload = {
            "model": self.model_name,
            "input": list(texts),
        }

        req = request.Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
        except error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="ignore") if hasattr(e, "read") else str(e)
            raise EmbedderError(f"Embedding request failed: {e.code} {detail}") from e
        except Exception as e:
            raise EmbedderError(f"Embedding request failed: {e}") from e

        data = self._safe_json_loads(body)
        if not isinstance(data, dict):
            raise EmbedderError("Embedding provider returned an invalid payload.")

        try:
            rows = data["data"]
            vectors = [row["embedding"] for row in rows]
            return [[float(x) for x in vec] for vec in vectors]
        except Exception as e:
            raise EmbedderError("Embedding response did not contain vectors.") from e

    def _local_embed(self, text: str) -> List[float]:
        """
        Deterministic local embedding fallback for development/demo use.

        It is not a semantic embedding model, but it keeps the pipeline usable
        when a remote embedding service is not available.
        """
        vec = [0.0] * self.local_dimension
        tokens = self._tokenize(text)
        if not tokens:
            return self._zero_vector()

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            # Spread token signal across the vector
            for i in range(0, len(digest), 2):
                idx = (digest[i] << 8 | digest[i + 1]) % self.local_dimension
                sign = 1.0 if (digest[i] % 2 == 0) else -1.0
                vec[idx] += sign * (1.0 / (1 + i // 2))

        return self._normalize(vec)

    def _tokenize(self, text: str) -> List[str]:
        text = text.lower()
        tokens = []
        current = []
        for ch in text:
            if ch.isalnum():
                current.append(ch)
            else:
                if current:
                    token = "".join(current)
                    if len(token) > 1:
                        tokens.append(token)
                    current = []
        if current:
            token = "".join(current)
            if len(token) > 1:
                tokens.append(token)
        return tokens

    def _normalize(self, vec: List[float]) -> List[float]:
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0:
            return self._zero_vector()
        return [v / norm for v in vec]

    def _zero_vector(self) -> List[float]:
        return [0.0] * self.local_dimension

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        headers.update(self.extra_headers)
        return headers

    def _safe_json_loads(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            loaded = json.loads(text)
            if isinstance(loaded, dict):
                return loaded
            return None
        except Exception:
            return None

    def _is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip() != "your api key")