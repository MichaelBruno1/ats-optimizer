"""LLM Provider abstraction layer.

Decouples agent implementations from LiteLLM and specific model providers.
Handles retries, exponential backoff with jitter, error logging, and context adjustment.
"""

import asyncio
import logging
import random
from typing import Any, Protocol, Type, TypeVar
from pydantic import BaseModel

import litellm

from app.config import settings

logger = logging.getLogger(__name__)

litellm.set_verbose = False  # type: ignore[attr-defined]

T = TypeVar("T", bound=BaseModel)


class LLMProvider(Protocol):
    """Protocol defining the unified LLM Provider interface."""

    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        ...

    async def generate_json(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        ...


class LiteLLMProvider:
    """Production implementation of LLMProvider wrapping LiteLLM."""

    def __init__(
        self,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> None:
        self.model = model or self._build_model_string()
        self.temperature = temperature if temperature is not None else settings.llm_temperature
        self.max_tokens = max_tokens or settings.llm_max_tokens

    @staticmethod
    def _build_model_string() -> str:
        provider = settings.llm_provider.lower().strip()
        model = settings.llm_model.strip()

        known_providers = {
            "openai", "ollama", "gemini", "anthropic", "azure", "cohere",
            "mistral", "openrouter", "vertex_ai", "groq", "together_ai",
            "huggingface", "replicate"
        }

        if "/" in model:
            prefix = model.split("/", 1)[0].lower()
            if prefix in known_providers:
                return model

        return f"{provider}/{model}"

    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens or self.max_tokens

        extra_kwargs: dict[str, Any] = {}
        resolved_provider = self.model.split("/", 1)[0].lower() if "/" in self.model else settings.llm_provider.lower()

        if settings.llm_api_key:
            extra_kwargs["api_key"] = settings.llm_api_key
        elif resolved_provider in ("openai", "ollama", "openrouter"):
            extra_kwargs["api_key"] = "local"

        if settings.llm_api_base and resolved_provider in ("openai", "ollama", "openrouter"):
            extra_kwargs["api_base"] = settings.llm_api_base

        if resolved_provider == "gemini":
            extra_kwargs["safety_settings"] = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]

        for attempt in range(3):
            try:
                response = await litellm.acompletion(
                    model=self.model,
                    messages=messages,
                    temperature=temp,
                    max_tokens=tokens,
                    **extra_kwargs,
                )
                raw_content = response.choices[0].message.content or ""  # type: ignore[union-attr]
                if not raw_content.strip():
                    raise ValueError("Empty response received from LLM")
                return raw_content
            except Exception as exc:
                if attempt < 2:
                    delay = (2 ** attempt) + random.uniform(0.1, 0.5)
                    logger.warning("LLM attempt %d failed: %s. Retrying in %.2fs...", attempt + 1, exc, delay)
                    await asyncio.sleep(delay)
                else:
                    logger.error("LLM call failed after 3 attempts: %s", exc)
                    raise RuntimeError(f"LLM invocation failed: {exc}") from exc

        return ""

    async def generate_json(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        from app.llm.structured_output import parse_json_from_llm
        raw_text = await self.generate(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return parse_json_from_llm(raw_text)
