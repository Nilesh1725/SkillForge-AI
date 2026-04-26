"""
Robust JSON extraction and parsing utilities.

LLaMA models frequently wrap JSON in markdown fences, add explanatory text,
or produce slightly malformed output.  This module handles all of that.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Type, TypeVar

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def _strip_markdown_fences(raw: str) -> str:
    """Strip markdown code fences from LLM output (handles missing closing fence too)."""
    raw = re.sub(r"^```[a-zA-Z]*\s*\n?", "", raw.strip(), flags=re.IGNORECASE)
    raw = re.sub(r"\n?```\s*$", "", raw.strip())
    return raw.strip()


def extract_json_string(raw: str) -> str:
    """
    Extract the first JSON object or array from a raw LLM response.

    Handles:
      - ```json ... ``` fences (with or without closing fence)
      - Leading/trailing prose
      - Nested braces
    """
    # Strip markdown fences first before any brace-walking
    cleaned = _strip_markdown_fences(raw)

    # Try direct parse of stripped content first
    try:
        json.loads(cleaned)
        return cleaned
    except json.JSONDecodeError:
        pass

    # Find the first { ... } or [ ... ] block
    brace_start = cleaned.find("{")
    bracket_start = cleaned.find("[")

    if brace_start == -1 and bracket_start == -1:
        raise ValueError("No JSON object or array found in LLM response")

    # Pick whichever comes first
    if brace_start == -1:
        start = bracket_start
        open_char, close_char = "[", "]"
    elif bracket_start == -1:
        start = brace_start
        open_char, close_char = "{", "}"
    else:
        if brace_start < bracket_start:
            start = brace_start
            open_char, close_char = "{", "}"
        else:
            start = bracket_start
            open_char, close_char = "[", "]"

    # Walk through to find the matching closing character
    depth = 0
    in_string = False
    escape_next = False
    end = start

    for i in range(start, len(cleaned)):
        ch = cleaned[i]

        if escape_next:
            escape_next = False
            continue

        if ch == "\\":
            escape_next = True
            continue

        if ch == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if ch == open_char:
            depth += 1
        elif ch == close_char:
            depth -= 1
            if depth == 0:
                end = i
                break

    if depth != 0:
        raise ValueError("Unbalanced braces/brackets in LLM response")

    return cleaned[start : end + 1]


def _fix_common_json_issues(json_str: str) -> str:
    """Attempt to fix common JSON issues from LLM output."""
    # Remove trailing commas before } or ]
    fixed = re.sub(r",\s*([}\]])", r"\1", json_str)
    # Replace single quotes with double quotes (only outside existing double-quoted strings)
    if '"' not in fixed:
        fixed = fixed.replace("'", '"')
    # Remove control characters
    fixed = re.sub(r"[\x00-\x1f]", " ", fixed)
    return fixed


def parse_json_response(raw: str) -> dict[str, Any] | list[Any]:
    """
    Parse a raw LLM response into a Python dict/list.
    Applies multiple recovery strategies.
    """
    # Strategy 1: Direct parse
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        pass

    # Strategy 2: Strip fences then direct parse
    try:
        stripped = _strip_markdown_fences(raw)
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    # Strategy 3: Extract JSON substring and parse
    try:
        json_str = extract_json_string(raw)
        return json.loads(json_str)
    except (ValueError, json.JSONDecodeError):
        pass

    # Strategy 4: Fix common issues and retry
    try:
        json_str = extract_json_string(raw)
        fixed = _fix_common_json_issues(json_str)
        return json.loads(fixed)
    except (ValueError, json.JSONDecodeError) as exc:
        logger.error("All JSON parsing strategies failed for response: %s...", raw[:200])
        raise ValueError(f"Failed to parse JSON from LLM response: {exc}") from exc


def parse_and_validate(raw: str, model: Type[T]) -> T:
    """
    Parse raw LLM text into a validated Pydantic model instance.

    Raises:
        ValueError: If JSON cannot be extracted.
        ValidationError: If the data does not match the schema.
    """
    data = parse_json_response(raw)
    try:
        return model.model_validate(data)
    except ValidationError:
        # If the parsed data is a list but the model expects an object with a list field,
        # try wrapping it
        if isinstance(data, list):
            # Attempt to find the first list field and wrap
            for field_name, field_info in model.model_fields.items():
                origin = getattr(field_info.annotation, "__origin__", None)
                if origin is list:
                    return model.model_validate({field_name: data})
        raise
