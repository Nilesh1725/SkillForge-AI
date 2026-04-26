"""
/generate-questions endpoint — adaptive interview question generation.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from models.schemas import GenerateQuestionsRequest, GenerateQuestionsResponse
from services.question_generator import generate_questions
from utils.llm_client import LLMError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Interview"])


@router.post(
    "/generate-questions",
    response_model=GenerateQuestionsResponse,
    summary="Generate interview questions",
    description="Generate adaptive interview questions for a specific skill and difficulty level.",
)
async def generate_interview_questions(request: GenerateQuestionsRequest) -> GenerateQuestionsResponse:
    """
    Generate interview questions based on skill, difficulty, and optional context.

    The difficulty adapts based on previous evaluation scores:
      - score > 7 → hard
      - score < 4 → easy
      - otherwise → medium
    """
    try:
        result = await generate_questions(
            skill=request.skill,
            difficulty=request.difficulty.value,
            count=request.count,
            context=request.context,
        )
        return result

    except LLMError as exc:
        logger.error("LLM error during question generation: %s", exc)
        raise HTTPException(status_code=502, detail=f"LLM service error: {exc}") from exc
    except Exception as exc:
        logger.error("Unexpected error during question generation: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during question generation") from exc
