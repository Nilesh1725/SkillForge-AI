"""
Skill matching service — deterministic matching using explicit synonym maps.

Reliable 5-layer system:
  1. Exact string match (case-insensitive)
  2. Synonym/equivalence lookup via skill_mappings
  3. Sub-skill hierarchy match
  4. Inferred match from resume sections
  5. Contextual match from project descriptions (via SEMANTIC_RELATIONS)
"""

from __future__ import annotations

import logging

from models.schemas import SkillMatch
from services.skill_mappings import (
    normalize_skill,
    are_semantically_equivalent,
    is_sub_skill_of,
    are_contextually_related,
    clean_skill_modifiers,
    SKILL_HIERARCHY,
)
from services.proficiency_engine import score_proficiency, SkillEvidence

logger = logging.getLogger(__name__)


def _find_match_in_resume_skills(
    jd_skill: str,
    resume_skills_lower: dict[str, str],
) -> tuple[bool, str]:
    """
    Try to match a JD skill against resume skills using exact + synonym matching.

    Args:
        jd_skill: The JD skill to match.
        resume_skills_lower: Dict of lowered resume skill → original resume skill.

    Returns:
        (found, match_method) where match_method is "exact" or "synonym".
    """
    jd_lower = jd_skill.lower().strip()

    # Layer 1: Exact match
    if jd_lower in resume_skills_lower:
        return True, "exact"

    # Layer 2: Synonym matching — check if any resume skill is semantically equivalent
    jd_canonical = normalize_skill(jd_skill)
    for resume_lower, resume_original in resume_skills_lower.items():
        resume_canonical = normalize_skill(resume_original)
        if jd_canonical == resume_canonical:
            return True, "synonym"

    # Layer 2.5: Safe modifier matching (Base Words)
    jd_clean = clean_skill_modifiers(jd_skill)
    for resume_lower, resume_original in resume_skills_lower.items():
        resume_clean = clean_skill_modifiers(resume_original)
        if jd_clean == resume_clean:
            return True, "modifier-clean"

    return False, ""


def _check_inferred_match(
    jd_skill: str,
    resume_sections: dict,
) -> tuple[bool, str]:
    """
    Check if a JD skill appears in inferred skills from resume sections
    (projects, certifications, experience).

    Returns:
        (found, match_method) — method is "inferred" if found.
    """
    if not resume_sections:
        return False, ""

    jd_canonical = normalize_skill(jd_skill)

    # Check projects
    for proj in resume_sections.get("projects", []):
        if isinstance(proj, dict):
            for inf in proj.get("inferred_skills", []):
                if are_semantically_equivalent(inf, jd_skill):
                    return True, "inferred"

    # Check certifications
    for cert in resume_sections.get("certifications", []):
        if isinstance(cert, dict):
            for inf in cert.get("inferred_skills", []):
                if are_semantically_equivalent(inf, jd_skill):
                    return True, "inferred"

    # Check experience
    for exp in resume_sections.get("experience", []):
        if isinstance(exp, dict):
            for inf in exp.get("inferred_skills", []):
                if are_semantically_equivalent(inf, jd_skill):
                    return True, "inferred"

    # Check skills section
    for skill in resume_sections.get("skills", []):
        if isinstance(skill, str) and are_semantically_equivalent(skill, jd_skill):
            return True, "inferred"

    return False, ""


def _check_contextual_project_match(
    jd_skill: str,
    resume_sections: dict,
) -> tuple[bool, str]:
    """
    Check if a JD skill is contextually related to any project
    name or description in resume_sections.

    Scoped to PROJECTS ONLY to avoid false positives.

    Returns:
        (found, match_method) — method is "contextual" if found.
    """
    if not resume_sections:
        return False, ""

    for proj in resume_sections.get("projects", []):
        if isinstance(proj, dict):
            proj_name = proj.get("name", "")
            proj_desc = proj.get("description", "")
            proj_text = f"{proj_name} {proj_desc}"
            if are_contextually_related(proj_text, jd_skill):
                return True, "contextual"

    return False, ""


async def match_skills(
    jd_skills: list[str],
    resume_skills: list[str],
    resume_text: str = "",
    resume_sections: dict | None = None,
) -> tuple[list[SkillMatch], set[str]]:
    """
    Match JD skills against resume skills using deterministic 5-layer matching:
      1. Exact string match (case-insensitive)
      2. Synonym/equivalence lookup
      3. Sub-skill hierarchy match (e.g. Pandas → Data Analysis)
      4. Inferred match from resume sections
      5. Contextual match from project descriptions (via SEMANTIC_RELATIONS)

    Tracks which resume skills are "used" to satisfy JD requirements,
    so they can be excluded from the extra-skills list.

    Args:
        jd_skills: Skills required by the job description.
        resume_skills: Skills found in the resume.
        resume_text: Full raw resume text (for proficiency scoring).
        resume_sections: LLM-parsed section annotations.

    Returns:
        Tuple of:
          - List of SkillMatch objects with evidence and proficiency data.
          - Set of used resume skill names (lowercase) that satisfied JD skills.
    """
    logger.info(
        "Matching %d JD skills against %d resume skills (deterministic)",
        len(jd_skills),
        len(resume_skills),
    )

    # Build lookup dict for resume skills
    resume_skills_lower: dict[str, str] = {}
    for s in resume_skills:
        key = s.lower().strip()
        if key not in resume_skills_lower:
            resume_skills_lower[key] = s

    matches: list[SkillMatch] = []
    seen_skills: set[str] = set()  # Avoid duplicate JD skills
    used_skills: set[str] = set()  # Track resume skills consumed by matching

    for jd_skill in jd_skills:
        jd_lower = jd_skill.lower().strip()
        if jd_lower in seen_skills:
            continue
        seen_skills.add(jd_lower)

        # Try matching
        found = False
        match_method = ""

        # Layer 1 + 2: Exact + synonym
        found, match_method = _find_match_in_resume_skills(jd_skill, resume_skills_lower)

        if found:
            # Mark the directly matched resume skill as used
            jd_canonical = normalize_skill(jd_skill).lower()
            for r_lower in resume_skills_lower:
                r_canonical = normalize_skill(resume_skills_lower[r_lower]).lower()
                if r_canonical == jd_canonical or r_lower == jd_lower:
                    used_skills.add(r_lower)

        # Layer 3: Sub-skill hierarchy — check if any resume skill is a sub-skill of this JD skill
        if not found:
            jd_canonical_lower = normalize_skill(jd_skill).lower().strip()
            if jd_canonical_lower in SKILL_HIERARCHY:
                for r_lower, r_original in resume_skills_lower.items():
                    if is_sub_skill_of(r_original, jd_skill):
                        found = True
                        match_method = "sub-skill"
                        used_skills.add(r_lower)
                        # Don't break — collect all sub-skills that match

        # Even if already found, still mark sub-skills as used
        # (e.g. JD asks for "Data Analysis" matched directly, but
        #  resume also has "Pandas" which is a sub-skill)
        if found:
            jd_canonical_lower = normalize_skill(jd_skill).lower().strip()
            if jd_canonical_lower in SKILL_HIERARCHY:
                for r_lower, r_original in resume_skills_lower.items():
                    if is_sub_skill_of(r_original, jd_skill):
                        used_skills.add(r_lower)

        # Layer 4: Inferred from sections
        if not found and resume_sections:
            found, match_method = _check_inferred_match(jd_skill, resume_sections)

        # Layer 5: Contextual match from project descriptions only
        if not found and resume_sections:
            found, match_method = _check_contextual_project_match(jd_skill, resume_sections)

        # Calculate proficiency using evidence engine
        evidence = SkillEvidence()
        if resume_text:
            evidence = score_proficiency(
                skill=jd_skill,
                resume_text=resume_text,
                resume_sections=resume_sections,
            )

        # If proficiency engine found evidence but matcher didn't, trust the evidence
        if not found and evidence.raw_score > 0:
            found = True
            match_method = "inferred"

        proficiency_level = evidence.level if evidence.raw_score > 0 else "unknown"

        # Mark the JD skill itself as used (it's satisfied)
        if found:
            used_skills.add(jd_lower)

        matches.append(
            SkillMatch(
                skill=jd_skill,
                found_in_resume=found,
                proficiency_estimate=proficiency_level,
                proficiency_score=evidence.raw_score,
                evidence_sources=evidence.source_tags,
                matched_via=match_method,
            )
        )

    found_count = sum(1 for m in matches if m.found_in_resume)
    logger.info(
        "Matching complete: %d/%d skills found (layers: exact+synonym+sub-skill+inferred+contextual), %d resume skills used",
        found_count,
        len(matches),
        len(used_skills),
    )

    return matches, used_skills
