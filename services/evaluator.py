"""
Answer evaluation service — scores candidate answers with structured JSON output.
"""

from __future__ import annotations

import logging

from models.schemas import EvaluateResponse, EvaluationResult
from utils.llm_client import query_llm_structured
from utils.prompts import EVALUATION_PROMPT
from utils.validators import determine_difficulty

logger = logging.getLogger(__name__)


async def evaluate_answer(
    question: str,
    answer: str,
    skill: str,
    difficulty: str = "medium",
) -> EvaluateResponse:
    """
    Evaluate a candidate's answer to an interview question.

    The LLM scores the answer across 4 dimensions and provides:
      - Numerical scores (0-10)
      - Constructive feedback
      - A model correct answer
      - Adaptive next difficulty recommendation

    Args:
        question: The interview question asked.
        answer: The candidate's answer.
        skill: The skill being tested.
        difficulty: Current difficulty level.

    Returns:
        EvaluateResponse with scores, feedback, and next difficulty.
    """
    prompt = EVALUATION_PROMPT.format(
        skill=skill,
        difficulty=difficulty,
        question=question,
        answer=answer,
    )

    logger.info("Evaluating answer for skill=%s, difficulty=%s", skill, difficulty)

    evaluation = await query_llm_structured(
        prompt=prompt,
        response_model=EvaluationResult,
        temperature=0.2,  # Low temp for consistent scoring
    )

    # Recalculate final_score to ensure correctness
    # Weights: concept 30%, practical 30%, clarity 20%, confidence 20%
    calculated_score = (
        evaluation.conceptual_understanding * 0.30
        + evaluation.practical_knowledge * 0.30
        + evaluation.clarity * 0.20
        + evaluation.confidence * 0.20
    )
    evaluation.final_score = round(calculated_score, 2)

    # Determine adaptive next difficulty
    next_difficulty = determine_difficulty(evaluation.final_score)

    logger.info(
        "Evaluation complete: final_score=%.2f, next_difficulty=%s",
        evaluation.final_score,
        next_difficulty,
    )

    return EvaluateResponse(
        skill=skill,
        difficulty=difficulty,
        evaluation=evaluation,
        next_difficulty=next_difficulty,
    )
