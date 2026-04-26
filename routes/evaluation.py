"""
/evaluate, /gap-analysis endpoints — answer evaluation and gap analysis.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from models.schemas import (
    EvaluateRequest,
    EvaluateResponse,
    GapAnalysisRequest,
    GapAnalysisResponse,
)
from services.evaluator import evaluate_answer
from services.gap_analysis import analyze_gaps
from utils.llm_client import LLMError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Evaluation"])


@router.post(
    "/evaluate",
    response_model=EvaluateResponse,
    summary="Evaluate candidate answer",
    description="Score a candidate's answer with structured evaluation and adaptive difficulty.",
)
async def evaluate(request: EvaluateRequest) -> EvaluateResponse:
    """
    Evaluate a candidate's answer to an interview question.

    Returns structured scores (0-10) for:
      - conceptual_understanding
      - practical_knowledge
      - clarity
      - confidence
      - final_score (weighted average)
      - feedback (constructive)
      - correct_answer (model answer)
      - next_difficulty (adaptive)
    """
    try:
        result = await evaluate_answer(
            question=request.question,
            answer=request.answer,
            skill=request.skill,
            difficulty=request.difficulty.value,
        )
        return result

    except LLMError as exc:
        logger.error("LLM error during evaluation: %s", exc)
        raise HTTPException(status_code=502, detail=f"LLM service error: {exc}") from exc
    except Exception as exc:
        logger.error("Unexpected error during evaluation: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during evaluation") from exc


@router.post(
    "/gap-analysis",
    response_model=GapAnalysisResponse,
    summary="Analyze skill gaps",
    description="Categorize skill gaps by priority based on evaluation scores.",
)
async def gap_analysis(request: GapAnalysisRequest) -> GapAnalysisResponse:
    """
    Perform gap analysis on candidate skills.

    Priority rules:
      - Required + score < 5 → HIGH
      - Required + score ≤ 7 → MEDIUM
      - Otherwise → LOW
    """
    try:
        result = await analyze_gaps(
            required_skills=request.required_skills,
            scores=request.scores,
        )
        return result

    except LLMError as exc:
        logger.error("LLM error during gap analysis: %s", exc)
        raise HTTPException(status_code=502, detail=f"LLM service error: {exc}") from exc
    except Exception as exc:
        logger.error("Unexpected error during gap analysis: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during gap analysis") from exc
