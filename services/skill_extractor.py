"""
Skill extraction service — uses LLM to extract skills from JD and resume text.

Now returns section-annotated skills for use by the proficiency engine.
"""

from __future__ import annotations

import logging

from models.schemas import ExtractedSkills, ExtractedSkillsDetailed
from utils.llm_client import query_llm_json
from utils.prompts import SKILL_EXTRACTION_PROMPT

logger = logging.getLogger(__name__)


async def extract_skills(
    job_description: str, resume: str
) -> ExtractedSkillsDetailed:
    """
    Extract skills from a job description and resume using the LLM.

    Returns:
        ExtractedSkillsDetailed with jd_skills, resume_skills, and resume_sections.
    """
    prompt = SKILL_EXTRACTION_PROMPT.format(
        job_description=job_description,
        resume=resume,
    )

    logger.info(
        "Extracting skills from JD (%d chars) and resume (%d chars)",
        len(job_description),
        len(resume),
    )

    raw_result = await query_llm_json(prompt=prompt, temperature=0.2)

    # Parse the result — handle both old and new format
    if not isinstance(raw_result, dict):
        logger.warning("LLM returned non-dict result, using defaults")
        raw_result = {}

    jd_skills = raw_result.get("jd_skills", [])
    resume_skills = raw_result.get("resume_skills", [])
    resume_sections = raw_result.get("resume_sections", {})

    # Normalize: strip whitespace, remove empties
    jd_skills = [s.strip() for s in jd_skills if isinstance(s, str) and s.strip()]
    resume_skills = [s.strip() for s in resume_skills if isinstance(s, str) and s.strip()]

    # If LLM returned resume_sections with inferred skills, merge them into resume_skills
    if resume_sections:
        all_section_skills: set[str] = set()

        # Profile/Objective/Summary section
        for s in resume_sections.get("profile", []):
            if isinstance(s, str) and s.strip():
                all_section_skills.add(s.strip())

        # Skills section
        for s in resume_sections.get("skills", []):
            if isinstance(s, str) and s.strip():
                all_section_skills.add(s.strip())

        # Projects
        for proj in resume_sections.get("projects", []):
            if isinstance(proj, dict):
                for s in proj.get("inferred_skills", []):
                    if isinstance(s, str) and s.strip():
                        all_section_skills.add(s.strip())

        # Certifications
        for cert in resume_sections.get("certifications", []):
            if isinstance(cert, dict):
                for s in cert.get("inferred_skills", []):
                    if isinstance(s, str) and s.strip():
                        all_section_skills.add(s.strip())

        # Experience
        for exp in resume_sections.get("experience", []):
            if isinstance(exp, dict):
                for s in exp.get("inferred_skills", []):
                    if isinstance(s, str) and s.strip():
                        all_section_skills.add(s.strip())

        # Achievements
        for ach in resume_sections.get("achievements", []):
            if isinstance(ach, dict):
                for s in ach.get("inferred_skills", []):
                    if isinstance(s, str) and s.strip():
                        all_section_skills.add(s.strip())

        # Merge into resume_skills (dedup)
        existing_lower = {s.lower() for s in resume_skills}
        for s in all_section_skills:
            if s.lower() not in existing_lower:
                resume_skills.append(s)
                existing_lower.add(s.lower())

    logger.info(
        "Extracted %d JD skills, %d resume skills, sections=%s",
        len(jd_skills),
        len(resume_skills),
        bool(resume_sections),
    )

    return ExtractedSkillsDetailed(
        jd_skills=jd_skills,
        resume_skills=resume_skills,
        resume_sections=resume_sections,
    )
