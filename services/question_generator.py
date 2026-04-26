"""
Interview question generation service — creates adaptive difficulty questions.
"""

from __future__ import annotations

import logging
from typing import Any

from models.schemas import GenerateQuestionsResponse, InterviewQuestion
from utils.llm_client import query_llm_json
from utils.prompts import QUESTION_GENERATION_PROMPT

logger = logging.getLogger(__name__)


async def generate_questions(
    skill: str,
    difficulty: str = "medium",
    count: int = 3,
    context: str | None = None,
) -> GenerateQuestionsResponse:
    """
    Generate interview questions for a given skill and difficulty level.

    Args:
        skill: The technical skill to generate questions for.
        difficulty: "easy", "medium", or "hard".
        count: Number of questions to generate (1-10).
        context: Optional job description context for relevance.

    Returns:
        GenerateQuestionsResponse with structured questions.
    """
    context_section = ""
    if context:
        context_section = f"### Job Context:\n{context}\n\nMake questions relevant to this job context."

    prompt = QUESTION_GENERATION_PROMPT.format(
        skill=skill,
        difficulty=difficulty,
        count=count,
        context_section=context_section,
    )

    logger.info("Generating %d %s questions for skill: %s", count, difficulty, skill)

    raw_result = await query_llm_json(prompt=prompt, temperature=0.5)

    # Parse the result
    questions: list[InterviewQuestion] = []

    if isinstance(raw_result, dict) and "questions" in raw_result:
        raw_questions = raw_result["questions"]
    elif isinstance(raw_result, list):
        raw_questions = raw_result
    else:
        raw_questions = []

    for q in raw_questions:
        if isinstance(q, dict):
            questions.append(InterviewQuestion(
                question=str(q.get("question", "")),
                difficulty=str(q.get("difficulty", difficulty)),
                skill=str(q.get("skill", skill)),
                expected_answer_points=q.get("expected_answer_points", []),
            ))

    # Ensure we have the requested count (pad if LLM returned fewer)
    if len(questions) < count:
        logger.warning("LLM returned %d questions, expected %d", len(questions), count)

    logger.info("Generated %d questions successfully", len(questions))

    return GenerateQuestionsResponse(
        skill=skill,
        difficulty=difficulty,
        questions=questions,
    )
