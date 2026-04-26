"""
/analyze endpoint — skill extraction and matching.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from models.schemas import AnalyzeRequest, AnalyzeResponse, SkillMatch
from services.skill_extractor import extract_skills
from services.skill_matcher import match_skills
from services.skill_mappings import normalize_skill
from utils.llm_client import LLMError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Analysis"])


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    summary="Extract and match skills",
    description="Extracts skills from a job description and resume, then matches them.",
)
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    Extract skills from JD + resume and match them.
    """
    try:
        # Step 1: Extract skills (now returns sections too)
        extracted = await extract_skills(
            job_description=request.job_description,
            resume=request.resume,
        )

        # Safety: ensure lists exist
        jd_skills = extracted.jd_skills or []
        resume_skills = extracted.resume_skills or []
        resume_sections = extracted.resume_sections or {}

        # Step 2: Match skills (deterministic — no FAISS/LLM)
        matched, used_skills = await match_skills(
            jd_skills=jd_skills,
            resume_skills=resume_skills,
            resume_text=request.resume,
            resume_sections=resume_sections,
        )

        # Step 3: Calculate match percentage
        # Formula: unique_matched_jd_skills / unique_jd_skills * 100
        unique_jd = set()
        for m in matched:
            unique_jd.add(m.skill.lower().strip())

        total = len(unique_jd)
        found_count = sum(1 for m in matched if m.found_in_resume)

        if total == 0:
            match_pct = 0.0
        else:
            match_pct = round((found_count / total) * 100, 2)

        # 🚨 Clamp value to prevent Pydantic crash
        match_pct = max(0.0, min(match_pct, 100.0))

        # Step 4: Missing skills — only truly missing
        missing = [m.skill for m in matched if not m.found_in_resume]

        # Step 5: Extra skills — resume skills not used to satisfy any JD requirement
        jd_canonicals = {normalize_skill(s).lower() for s in jd_skills}
        extra_skills: list[str] = []
        seen_extra: set[str] = set()
        for s in resume_skills:
            s_lower = s.lower().strip()
            canonical_lower = normalize_skill(s).lower()
            # Skip if: already in JD, already used to satisfy a JD skill, or already listed
            if (canonical_lower in jd_canonicals
                    or s_lower in used_skills
                    or canonical_lower in seen_extra):
                continue
            extra_skills.append(s)
            seen_extra.add(canonical_lower)

        # Step 6: Proficiency summary
        proficiency_summary: dict[str, str] = {}
        for m in matched:
            proficiency_summary[m.skill] = m.proficiency_estimate

        return AnalyzeResponse(
            jd_skills=jd_skills,
            resume_skills=resume_skills,
            matched_skills=matched,
            match_percentage=match_pct,
            missing_skills=missing,
            extra_skills=extra_skills,
            proficiency_summary=proficiency_summary,
        )

    except LLMError as exc:
        logger.error("LLM error during analysis: %s", exc)
        raise HTTPException(
            status_code=502,
            detail=f"LLM service error: {exc}"
        ) from exc

    except Exception as exc:
        logger.error("Unexpected error during analysis: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=str(exc)  # 👈 shows real error during debugging
        ) from exc