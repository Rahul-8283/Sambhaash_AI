# services/llm/llm_client.py

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Sequence
from urllib import error, request

from .prompt_builder import PromptBundle


class LLMClientError(RuntimeError):
    pass


class LLMClient:
    """
    OpenAI-compatible chat client for the orchestration layer.

    This class is intentionally small:
    - takes a PromptBundle
    - sends system + user messages
    - returns raw model text

    The orchestrator remains the control layer.
    """

    def __init__(
        self,
        model_name: str = "model name",
        api_key: str = "your api key",
        base_url: str = "https://api.openai.com/v1",
        timeout: int = 30,
        default_temperature: float = 0.2,
        default_max_tokens: int = 700,
        extra_headers: Optional[Dict[str, str]] = None,
        response_format_json: bool = False,
    ) -> None:
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.default_temperature = default_temperature
        self.default_max_tokens = default_max_tokens
        self.extra_headers = extra_headers or {}
        self.response_format_json = response_format_json

    def __call__(self, bundle: PromptBundle) -> str:
        return self.generate(bundle)

    def generate(
        self,
        bundle: PromptBundle | Dict[str, Any] | str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Send the prompt bundle to the model and return raw text.
        """
        if isinstance(bundle, str):
            system_prompt = "You are a helpful assistant."
            user_prompt = bundle
            response_format = ""
            metadata = {}
        elif isinstance(bundle, dict):
            system_prompt = str(bundle.get("system_prompt", "You are a helpful assistant."))
            user_prompt = str(bundle.get("user_prompt", ""))
            response_format = str(bundle.get("response_format", ""))
            metadata = dict(bundle.get("metadata", {}) or {})
        else:
            system_prompt = bundle.system_prompt
            user_prompt = bundle.user_prompt
            response_format = bundle.response_format
            metadata = dict(bundle.metadata or {})

        messages = self._build_messages(system_prompt, user_prompt, response_format, metadata)
        return self._chat_completion(
            messages=messages,
            temperature=temperature if temperature is not None else self.default_temperature,
            max_tokens=max_tokens if max_tokens is not None else self.default_max_tokens,
        )

    def generate_json(
        self,
        bundle: PromptBundle | Dict[str, Any] | str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Convenience helper when the caller expects JSON output.
        """
        raw = self.generate(bundle, temperature=temperature, max_tokens=max_tokens)
        return self._extract_json_object(raw) or {}

    def _build_messages(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: str,
        metadata: Dict[str, Any],
    ) -> List[Dict[str, str]]:
        """
        Compose chat messages. The response_format is appended to the user turn
        so providers that lack strict JSON mode still receive the contract.
        """
        user_content_parts = [user_prompt.strip()]
        if response_format.strip():
            user_content_parts.append(response_format.strip())
        if metadata:
            user_content_parts.append(f"### METADATA\n{json.dumps(metadata, ensure_ascii=False, indent=2)}")

        return [
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": "\n\n".join(part for part in user_content_parts if part)},
        ]

    def _chat_completion(
        self,
        messages: Sequence[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        if not self.api_key or self.api_key.strip() == "your api key":
            raise LLMClientError(
                "LLMClient api_key is not configured. Replace 'your api key' with a real key."
            )

        url = f"{self.base_url}/chat/completions"
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": list(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if self.response_format_json:
            payload["response_format"] = {"type": "json_object"}

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
            raise LLMClientError(f"LLM request failed: {e.code} {detail}") from e
        except Exception as e:
            raise LLMClientError(f"LLM request failed: {e}") from e

        data = self._safe_json_loads(body)
        if not isinstance(data, dict):
            raise LLMClientError("LLM returned an invalid response payload.")

        try:
            content = data["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise KeyError
            return self._strip_code_fences(content.strip())
        except Exception as e:
            raise LLMClientError("LLM response did not contain message content.") from e

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
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

    def _extract_json_object(self, text: str) -> Optional[Dict[str, Any]]:
        if not text:
            return None
        cleaned = self._strip_code_fences(text).strip()
        data = self._safe_json_loads(cleaned)
        if isinstance(data, dict):
            return data
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if match:
            return self._safe_json_loads(match.group(0))
        return None

    def _strip_code_fences(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.IGNORECASE)
            text = re.sub(r"\s*```$", "", text.strip())
        return text