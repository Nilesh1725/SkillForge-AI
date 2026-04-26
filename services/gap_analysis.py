"""
Gap analysis service — categorizes skill gaps by priority.
"""

from __future__ import annotations

import logging

from models.schemas import GapAnalysisResponse, SkillGap
from utils.llm_client import query_llm_json
from utils.prompts import GAP_ANALYSIS_PROMPT
from utils.validators import determine_gap_priority, validate_scores

logger = logging.getLogger(__name__)


async def analyze_gaps(
    required_skills: list[str],
    scores: dict[str, float],
) -> GapAnalysisResponse:
    """
    Perform gap analysis on candidate skills.

    Logic:
      - Score < 5 for a required skill → HIGH priority
      - Score <= 7 for a required skill → MEDIUM priority
      - Score > 7 or not required → LOW priority

    Also gets LLM recommendations for each gap.

    Args:
        required_skills: List of required skill names.
        scores: Mapping of skill name → score (0-10).

    Returns:
        GapAnalysisResponse with categorized gaps and readiness score.
    """
    logger.info("Analyzing gaps for %d skills", len(required_skills))

    # Validate and clamp scores
    validated_scores = validate_scores(scores)

    # Build skills + scores string for the LLM
    skills_scores_text = "\n".join(
        f"- {skill}: {validated_scores.get(skill, 0.0)}/10 {'(REQUIRED)' if skill in required_skills else '(OPTIONAL)'}"
        for skill in set(list(required_skills) + list(validated_scores.keys()))
    )

    # Get LLM recommendations
    prompt = GAP_ANALYSIS_PROMPT.format(skills_scores=skills_scores_text)
    llm_recommendations: dict[str, str] = {}

    try:
        raw_result = await query_llm_json(prompt=prompt, temperature=0.3)
        if isinstance(raw_result, dict) and "gaps" in raw_result:
            for gap in raw_result["gaps"]:
                if isinstance(gap, dict):
                    llm_recommendations[gap.get("skill", "")] = gap.get("recommendation", "")
    except Exception as exc:
        logger.warning("LLM gap analysis recommendations failed: %s", exc)

    # Build gap list with deterministic priority logic (not relying on LLM)
    gaps: list[SkillGap] = []
    for skill in set(list(required_skills) + list(validated_scores.keys())):
        score = validated_scores.get(skill, 0.0)
        is_required = skill in required_skills
        priority = determine_gap_priority(score, is_required)

        gaps.append(SkillGap(
            skill=skill,
            score=score,
            priority=priority,
            is_required=is_required,
            recommendation=llm_recommendations.get(skill, f"Improve {skill} skills through practice and study."),
        ))

    # Sort: HIGH first, then MEDIUM, then LOW
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    gaps.sort(key=lambda g: (priority_order.get(g.priority, 3), -g.score))

    # Calculate counts
    high = sum(1 for g in gaps if g.priority == "HIGH")
    medium = sum(1 for g in gaps if g.priority == "MEDIUM")
    low = sum(1 for g in gaps if g.priority == "LOW")

    # Overall readiness = average score / 10 * 100 for required skills
    required_scores = [validated_scores.get(s, 0.0) for s in required_skills]
    overall_readiness = (sum(required_scores) / (len(required_scores) * 10) * 100) if required_scores else 0.0

    logger.info(
        "Gap analysis complete: HIGH=%d, MEDIUM=%d, LOW=%d, readiness=%.1f%%",
        high, medium, low, overall_readiness,
    )

    return GapAnalysisResponse(
        gaps=gaps,
        high_priority_count=high,
        medium_priority_count=medium,
        low_priority_count=low,
        overall_readiness=round(overall_readiness, 2),
    )
