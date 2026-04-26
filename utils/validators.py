"""
Validation helpers for LLM outputs and request data.
"""

from __future__ import annotations

import logging
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError

from utils.json_parser import parse_json_response

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def validate_llm_output(raw: str, model: Type[T]) -> T:
    """
    Validate raw LLM output against a Pydantic model.

    Steps:
      1. Parse raw text to JSON
      2. Validate against the Pydantic schema
      3. Return validated instance

    Raises:
        ValueError: If JSON extraction fails.
        ValidationError: If schema validation fails.
    """
    data = parse_json_response(raw)
    return model.model_validate(data)


def validate_scores(scores: dict[str, float]) -> dict[str, float]:
    """Ensure all scores are within 0-10 range."""
    validated: dict[str, float] = {}
    for skill, score in scores.items():
        if not isinstance(score, (int, float)):
            logger.warning("Invalid score type for %s: %s, defaulting to 0", skill, type(score))
            validated[skill] = 0.0
        else:
            validated[skill] = max(0.0, min(10.0, float(score)))
    return validated


def determine_difficulty(score: float) -> str:
    """Determine next question difficulty based on score (adaptive logic)."""
    if score > 7:
        return "hard"
    elif score < 4:
        return "easy"
    else:
        return "medium"


def determine_gap_priority(score: float, is_required: bool = True) -> str:
    """Determine skill gap priority based on score and requirement status."""
    if is_required and score < 5:
        return "HIGH"
    elif is_required and score <= 7:
        return "MEDIUM"
    else:
        return "LOW"


def safe_validate(data: dict, model: Type[T]) -> T | None:
    """
    Attempt to validate data against a model, returning None on failure
    instead of raising.
    """
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        logger.warning("Validation failed for %s: %s", model.__name__, exc)
        return None
