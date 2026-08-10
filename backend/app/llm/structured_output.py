"""Structured Output Utilities for Parsing, Validating and Repairing LLM JSON outputs."""

import json
import logging
import re
from typing import Any, Type, TypeVar
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def parse_json_from_llm(raw: str) -> dict[str, Any]:
    """Extract and parse JSON dict from raw LLM text.

    Supports:
    1. Direct json string.
    2. Markdown ```json code blocks.
    3. First '{' and last '}' extraction.
    4. Backtracking repair for truncated JSON responses.
    """
    cleaned = raw.strip()

    # 1. Direct parse
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # 2. Markdown code fences
    fence_pattern = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)
    match = fence_pattern.search(raw)
    if match:
        fence_content = match.group(1).strip()
        try:
            parsed = json.loads(fence_content)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    # 3. Substring between first { and last }
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            parsed = json.loads(raw[start : end + 1])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    # 4. Backtracking recovery for truncated JSON
    if start != -1:
        candidate_base = raw[start:]
        for i in range(len(candidate_base), 0, -1):
            trimmed = candidate_base[:i].strip()
            for suffix in ("", "}", '"}', '"]}', '"}]}', ']}', ']', '"]'):
                try:
                    parsed = json.loads(trimmed + suffix)
                    if isinstance(parsed, dict):
                        logger.warning(
                            "Repaired truncated JSON by backtracking (trimmed %d chars)",
                            len(candidate_base) - i,
                        )
                        return parsed
                except json.JSONDecodeError:
                    pass

    logger.error("Failed to parse JSON from response (%d chars): %r", len(raw), raw[:200])
    raise ValueError(f"Could not extract valid JSON from LLM output: {raw[:300]!r}")


def parse_and_validate(raw: str, schema_cls: Type[T]) -> T:
    """Parse raw LLM response as JSON and validate against a Pydantic model class."""
    json_dict = parse_json_from_llm(raw)
    try:
        return schema_cls.model_validate(json_dict)
    except ValidationError as exc:
        logger.error("Pydantic validation failed for %s: %s", schema_cls.__name__, exc)
        raise exc
