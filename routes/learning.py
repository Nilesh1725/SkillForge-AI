"""
/learning-plan endpoint — personalized learning roadmap generation.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from models.schemas import LearningPlanRequest, LearningPlanResponse
from services.learning_plan import generate_learning_plan
from utils.llm_client import LLMError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Learning"])


@router.post(
    "/learning-plan",
    response_model=LearningPlanResponse,
    summary="Generate learning plan",
    description="Generate a personalized learning roadmap based on skill gaps.",
)
async def learning_plan(request: LearningPlanRequest) -> LearningPlanResponse:
    """
    Generate a structured learning plan including:
      - Week-by-week topics
      - Daily time allocation
      - Recommended resources
      - Milestones
      - Adjacent skills
    """
    try:
        result = await generate_learning_plan(
            skill_gaps=request.skill_gaps,
            available_hours_per_day=request.available_hours_per_day,
            days_per_week=request.days_per_week,
            target_weeks=request.target_weeks,
        )
        return result

    except LLMError as exc:
        logger.error("LLM error during learning plan generation: %s", exc)
        raise HTTPException(status_code=502, detail=f"LLM service error: {exc}") from exc
    except Exception as exc:
        logger.error("Unexpected error during learning plan generation: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during learning plan generation") from exc
