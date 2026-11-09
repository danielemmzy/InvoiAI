"""
============================================================
Configurable AI Client for GL Coding Suggestions

Supports multiple providers via environment:
- OPENAI (default, backward compatible)
- GEMINI (Google Generative Language API, OpenAI-compatible)
- GROQ (OpenAI-compatible)
- LOCAL (Ollama or local OpenAI-compatible server)
- DISABLED (no AI calls, returns None immediately)

The client is intentionally minimal — JSON-mode chat completions only.
============================================================
"""

from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class AIClient(ABC):
    """Abstract AI client for structured JSON completions."""

    @abstractmethod
    async def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        timeout: float = 20.0,
    ) -> dict[str, Any] | None:
        """Return parsed JSON object or None on failure."""
        raise NotImplementedError


class OpenAIClient(AIClient):
    def __init__(self, api_key: str, base_url: str | None = None, model: str = "gpt-4o-mini", timeout: float = 20.0):
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=timeout, max_retries=1)
        self._model = model

    async def complete_json(self, *, system_prompt: str, user_prompt: str, temperature: float = 0.0, timeout: float = 20.0) -> dict[str, Any] | None:
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                temperature=temperature,
                timeout=timeout,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            content = response.choices[0].message.content
            return json.loads(content) if content else None
        except Exception as exc:
            logger.warning("OpenAI completion failed: %s", exc)
            return None


class DisabledClient(AIClient):
    """No-op client used when AI is disabled or no credentials."""

    async def complete_json(self, *, system_prompt: str, user_prompt: str, temperature: float = 0.0, timeout: float = 20.0) -> dict[str, Any] | None:
        return None


def create_ai_client() -> AIClient:
    """
    Factory that returns the configured AI client.

    Environment variables:
      AI_PROVIDER: "openai" | "gemini" | "groq" | "local" | "disabled"
      OPENAI_API_KEY / GEMINI_API_KEY / GROQ_API_KEY / LOCAL_API_KEY
      AI_BASE_URL (for gemini/groq/local)
      AI_MODEL (defaults per provider)
    """
    provider = os.getenv("AI_PROVIDER", "openai").lower().strip()

    if provider == "disabled":
        logger.info("AI provider: disabled (no AI calls will be made)")
        return DisabledClient()

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("AI_PROVIDER=openai but OPENAI_API_KEY not set; falling back to disabled")
            return DisabledClient()
        model = os.getenv("AI_MODEL", "gpt-4o-mini")
        logger.info("AI provider: openai (model=%s)", model)
        return OpenAIClient(api_key=api_key, model=model)

    if provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("AI_PROVIDER=gemini but GEMINI_API_KEY not set; falling back to disabled")
            return DisabledClient()
        base_url = os.getenv("AI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
        model = os.getenv("AI_MODEL", "gemini-2.0-flash")
        logger.info("AI provider: gemini (model=%s, base=%s)", model, base_url)
        return OpenAIClient(api_key=api_key, base_url=base_url, model=model)

    if provider == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.warning("AI_PROVIDER=groq but GROQ_API_KEY not set; falling back to disabled")
            return DisabledClient()
        base_url = os.getenv("AI_BASE_URL", "https://api.groq.com/openai/v1")
        model = os.getenv("AI_MODEL", "llama-3.1-8b-instant")
        logger.info("AI provider: groq (model=%s, base=%s)", model, base_url)
        return OpenAIClient(api_key=api_key, base_url=base_url, model=model)

    if provider == "local":
        base_url = os.getenv("AI_BASE_URL", "http://localhost:11434/v1")
        api_key = os.getenv("LOCAL_API_KEY", "ollama")
        model = os.getenv("AI_MODEL", "llama3.1:8b")
        logger.info("AI provider: local (model=%s, base=%s)", model, base_url)
        return OpenAIClient(api_key=api_key, base_url=base_url, model=model)

    logger.warning("Unknown AI_PROVIDER=%s; falling back to disabled", provider)
    return DisabledClient()