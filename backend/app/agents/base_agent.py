"""Base agent class providing shared LLM call infrastructure.

All concrete agents inherit from BaseAgent and call ``_invoke`` to
communicate with the configured LLM via LiteLLM.  Retry logic, JSON
extraction, and error handling are centralised here.
"""

import asyncio
import json
import logging
import random
import re
from pathlib import Path
from typing import Any

from functools import lru_cache
import litellm

from app.config import settings

logger = logging.getLogger(__name__)

# Disable LiteLLM's verbose logging in production
litellm.set_verbose = False  # type: ignore[attr-defined]

# Directory containing prompt .txt files
PROMPTS_DIR = Path(__file__).parent / "prompts"


@lru_cache(maxsize=16)
def _load_prompt_cached(filename: str) -> str:
    """Load and cache system prompt from disk."""
    prompt_path = PROMPTS_DIR / filename
    try:
        return prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise AgentError(
            f"System prompt file not found: {prompt_path}"
        ) from exc


class AgentError(Exception):
    """Raised when an agent fails to produce a valid response."""


class BaseAgent:
    """Abstract base for all LLM agents in the ATS Optimizer.

    Subclasses must define ``system_prompt_file`` pointing to a .txt file
    inside the ``prompts/`` directory.

    Attributes:
        system_prompt_file: Filename (not full path) of the system prompt.
        model: The LiteLLM model string, defaulting to the global config.
        temperature: Sampling temperature, defaulting to the global config.
        max_tokens: Max response tokens, defaulting to the global config.
    """

    system_prompt_file: str = ""

    def __init__(
        self,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> None:
        self.model = model or self._build_model_string()
        self.temperature = temperature if temperature is not None else settings.llm_temperature
        self.max_tokens = max_tokens or settings.llm_max_tokens
        self._system_prompt: str | None = None

    # ─────────────────────────────────────────────────────────────────────────
    # Model string construction
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _build_model_string() -> str:
        """Construct the LiteLLM model identifier from settings.

        LiteLLM requires the format ``provider/model`` for routing,
        especially when using custom/OpenAI-compatible endpoints or native providers.
        If a provider prefix (e.g., 'openai/', 'gemini/') is already in the model name,
        we use it as-is. Otherwise, we prefix it with the configured provider.

        Returns:
            LiteLLM-compatible model string.
        """
        provider = settings.llm_provider.lower().strip()
        model = settings.llm_model.strip()

        # If the model is already prefixed with a known provider, use it directly.
        # Some models contain a slash that is NOT a provider prefix (e.g., "google/gemma-4-e4b"
        # when called via an openai-compatible gateway).
        known_providers = {
            "openai", "ollama", "gemini", "anthropic", "azure", "cohere",
            "mistral", "openrouter", "vertex_ai", "groq", "together_ai",
            "huggingface", "replicate"
        }

        if "/" in model:
            prefix = model.split("/", 1)[0].lower()
            if prefix in known_providers:
                return model

        # If no known provider prefix is present, prepend the configured provider
        return f"{provider}/{model}"

    # ─────────────────────────────────────────────────────────────────────────
    # Prompt loading
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def system_prompt(self) -> str:
        """Lazily load and cache the system prompt from disk.

        Returns:
            The full text of the system prompt file.

        Raises:
            AgentError: If the prompt file cannot be found or read.
        """
        if not self.system_prompt_file:
            raise AgentError(
                f"{self.__class__.__name__} did not set 'system_prompt_file'."
            )
        return _load_prompt_cached(self.system_prompt_file)

    # ─────────────────────────────────────────────────────────────────────────
    # LLM invocation
    # ─────────────────────────────────────────────────────────────────────────

    async def _invoke(self, user_message: str) -> dict[str, Any]:
        """Call the LLM and return parsed JSON from the response.

        Sends a two-message conversation (system + user) to the configured
        model and parses the assistant's reply as JSON.

        Args:
            user_message: The user-turn content to send to the LLM.

        Returns:
            Parsed JSON response as a Python dict.

        Raises:
            AgentError: If the LLM call fails or the response is not valid JSON.
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message},
        ]

        extra_kwargs: dict[str, Any] = {}
        resolved_provider = self.model.split("/", 1)[0].lower() if "/" in self.model else settings.llm_provider.lower()

        if settings.llm_api_key:
            extra_kwargs["api_key"] = settings.llm_api_key
        elif resolved_provider in ("openai", "ollama", "openrouter"):
            extra_kwargs["api_key"] = "local"

        if settings.llm_api_base:
            if resolved_provider in ("openai", "ollama", "openrouter"):
                extra_kwargs["api_base"] = settings.llm_api_base

        resolved_provider = self.model.split("/", 1)[0].lower() if "/" in self.model else settings.llm_provider.lower()
        if resolved_provider == "gemini":
            extra_kwargs["safety_settings"] = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]

        logger.debug(
            "Invoking LLM model='%s' temperature=%.2f max_tokens=%d",
            self.model,
            self.temperature,
            self.max_tokens,
        )

        current_max_tokens = self.max_tokens
        response = None

        for attempt in range(3):
            try:
                response = await litellm.acompletion(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=current_max_tokens,
                    **extra_kwargs,
                )
                raw_content = response.choices[0].message.content or ""  # type: ignore[union-attr]
                if not raw_content.strip():
                    raise ValueError("Empty response received from LLM")
                break  # Success
            except Exception as exc:
                if attempt < 2:
                    exc_str = str(exc).lower()
                    # If it's a context size or empty response issue, reduce max_tokens
                    if "context size" in exc_str or "400" in exc_str or "bad request" in exc_str or "empty response" in exc_str:
                        new_tokens = int(current_max_tokens * 0.65)
                        if new_tokens >= 800:
                            logger.warning(
                                "LLM call failed for %s (context/empty). Retrying with reduced max_tokens=%d. Error: %s",
                                self.__class__.__name__,
                                new_tokens,
                                str(exc)
                            )
                            current_max_tokens = new_tokens
                            continue

                    # Exponential backoff delay with jitter
                    delay = (2 ** attempt) + random.uniform(0.1, 0.5)
                    logger.warning(
                        "LLM call failed for %s. Retrying attempt %d/3 in %.2fs. Error: %s",
                        self.__class__.__name__,
                        attempt + 2,
                        delay,
                        str(exc)
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.exception("LLM call failed for %s after all retry attempts", self.__class__.__name__)
                    raise AgentError(f"LLM invocation failed: {exc}") from exc

        logger.debug(
            "LLM response (%d chars): %s…", len(raw_content), raw_content[:120]
        )

        return self._parse_json(raw_content)

    # ─────────────────────────────────────────────────────────────────────────
    # JSON parsing
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any]:
        """Extract and parse JSON from the LLM's raw text response.

        Handles cases where the model wraps JSON in markdown code fences.

        Args:
            raw: Raw string from the LLM assistant message.

        Returns:
            Parsed Python dict.

        Raises:
            AgentError: If valid JSON cannot be extracted from the response.
        """
        cleaned = raw.strip()

        # 1. Try parsing the entire cleaned string first
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # 2. Try extracting from markdown code fences and validate with json.loads
        fence_pattern = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)
        match = fence_pattern.search(raw)
        if match:
            fence_content = match.group(1).strip()
            try:
                return json.loads(fence_content)
            except json.JSONDecodeError:
                pass

        # 3. Last-resort: find the first '{' and last '}' in the entire raw string
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(raw[start : end + 1])
            except json.JSONDecodeError:
                pass

        # 4. Backtracking recovery for truncated JSON (e.g. from context size limits)
        if start != -1:
            candidate_base = raw[start:]
            # Iterate backwards to find a point where we can repair
            for i in range(len(candidate_base), 0, -1):
                trimmed = candidate_base[:i].strip()
                # Try different closing bracket combinations to find a valid one
                for suffix in ("", "}", '"}', '"]}', '"}]}', ']}', ']', '"]'):
                    try:
                        parsed = json.loads(trimmed + suffix)
                        if isinstance(parsed, dict):
                            logger.warning(
                                "Successfully repaired truncated JSON response by backtracking (trimmed %d chars).",
                                len(candidate_base) - i
                            )
                            return parsed
                    except json.JSONDecodeError:
                        pass

        logger.error(
            "JSON parsing failed. Raw response length: %d. Start: %r... End: %r",
            len(raw), raw[:200], raw[-200:]
        )
        raise AgentError(
            f"LLM returned non-JSON content. Length: {len(raw)}. Preview: {raw[:300]!r}"
        )
