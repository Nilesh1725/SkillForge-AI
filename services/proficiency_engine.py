"""
Evidence-based proficiency scoring engine.

Scans the raw resume text across sections (Skills, Projects, Certifications,
Experience, Achievements) and assigns a deterministic proficiency score with
full evidence tracing.

Scoring weights (per your spec):
  Skills section mention   = +2
  Used in a Project        = +4  (first project)
  Additional projects      = +3  each
  Certification            = +3
  Achievement              = +2
  Experience               = +5
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from services.skill_mappings import normalize_skill, are_semantically_equivalent

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
#  Data structures
# ──────────────────────────────────────────────

@dataclass
class SkillEvidence:
    """Evidence collected for a single skill."""
    in_skills_section: bool = False
    in_profile_section: bool = False
    projects: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    experience: list[str] = field(default_factory=list)
    achievements: list[str] = field(default_factory=list)
    raw_score: int = 0
    level: str = "unknown"

    @property
    def source_tags(self) -> list[str]:
        """Human-readable list of evidence sources."""
        tags: list[str] = []
        if self.in_profile_section:
            tags.append("Profile")
        if self.in_skills_section:
            tags.append("Skills")
        for p in self.projects:
            tags.append(f"Project: {p}")
        for c in self.certifications:
            tags.append(f"Cert: {c}")
        for e in self.experience:
            tags.append(f"Exp: {e}")
        for a in self.achievements:
            tags.append(f"Achievement: {a}")
        return tags


# ──────────────────────────────────────────────
#  Section detection (regex-based)
# ──────────────────────────────────────────────

# Common resume section header patterns
_SECTION_PATTERNS: dict[str, re.Pattern] = {
    "skills": re.compile(
        r"(?:^|\n)\s*(?:technical\s+)?skills?\s*(?::|\n|—|–|-)",
        re.IGNORECASE,
    ),
    "projects": re.compile(
        r"(?:^|\n)\s*(?:academic\s+|personal\s+|key\s+)?projects?\s*(?::|\n|—|–|-)",
        re.IGNORECASE,
    ),
    "certifications": re.compile(
        r"(?:^|\n)\s*(?:certifications?|certificates?|licensed?)\s*(?::|\n|—|–|-)",
        re.IGNORECASE,
    ),
    "experience": re.compile(
        r"(?:^|\n)\s*(?:work\s+|professional\s+)?experience\s*(?::|\n|—|–|-)",
        re.IGNORECASE,
    ),
    "achievements": re.compile(
        r"(?:^|\n)\s*(?:achievements?|accomplishments?|awards?|honors?)\s*(?::|\n|—|–|-)",
        re.IGNORECASE,
    ),
    "education": re.compile(
        r"(?:^|\n)\s*education\s*(?::|\n|—|–|-)",
        re.IGNORECASE,
    ),
    "objective": re.compile(
        r"(?:^|\n)\s*(?:objective|summary|profile|about)\s*(?::|\n|—|–|-)",
        re.IGNORECASE,
    ),
}

# All known section header pattern (used to delimit sections)
_ANY_SECTION = re.compile(
    r"(?:^|\n)\s*(?:"
    r"(?:technical\s+)?skills?"
    r"|(?:academic\s+|personal\s+|key\s+)?projects?"
    r"|certifications?|certificates?"
    r"|(?:work\s+|professional\s+)?experience"
    r"|achievements?|accomplishments?|awards?|honors?"
    r"|education"
    r"|objective|summary|profile|about"
    r"|(?:tools?\s*(?:&|and)\s*)?technologies?"
    r"|interests?|hobbies?"
    r"|references?"
    r"|languages?"
    r")\s*(?::|\n|—|–|-)",
    re.IGNORECASE,
)


def _extract_sections(resume_text: str) -> dict[str, str]:
    """
    Split resume text into named sections.

    Returns a dict like:
      {"skills": "Python, SQL, ...", "projects": "Project 1 ...", ...}

    Sections not found will be absent from the dict.
    """
    sections: dict[str, str] = {}

    # Find all section header positions
    header_positions: list[tuple[str, int]] = []
    for name, pattern in _SECTION_PATTERNS.items():
        match = pattern.search(resume_text)
        if match:
            header_positions.append((name, match.end()))

    if not header_positions:
        # No sections detected — treat entire text as one blob
        return {"_full": resume_text}

    # Sort by position in text
    header_positions.sort(key=lambda x: x[1])

    # Find all section boundaries (including unknown headers)
    all_headers = list(_ANY_SECTION.finditer(resume_text))
    all_header_ends = sorted(set(m.end() for m in all_headers))

    for i, (name, start) in enumerate(header_positions):
        # Find the next section header after this one
        next_start = len(resume_text)
        for hend in all_header_ends:
            if hend > start + 5:  # skip self
                # Find the start of that header line
                for m in all_headers:
                    if m.end() == hend:
                        next_start = m.start()
                        break
                break

        sections[name] = resume_text[start:next_start].strip()

    return sections


# ──────────────────────────────────────────────
#  Skill mention detection
# ──────────────────────────────────────────────

def _skill_mentioned_in(text: str, skill: str) -> bool:
    """
    Check if a skill is mentioned in a text block.
    Uses word-boundary matching for the skill and its canonical form.
    """
    if not text or not skill:
        return False

    text_lower = text.lower()
    skill_lower = skill.lower().strip()

    # Direct substring check (word boundary aware for short skills)
    if len(skill_lower) <= 2:
        # For very short skills (R, Go, C), require word boundaries
        pattern = r'\b' + re.escape(skill_lower) + r'\b'
        if re.search(pattern, text_lower):
            return True
    else:
        if skill_lower in text_lower:
            return True

    # Also check canonical form
    canonical = normalize_skill(skill)
    canonical_lower = canonical.lower()
    if canonical_lower != skill_lower and canonical_lower in text_lower:
        return True

    return False


def _extract_project_names(projects_text: str) -> list[str]:
    """Extract individual project names/titles from a projects section."""
    lines = projects_text.split("\n")
    projects: list[str] = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Common patterns: "• Project Name", "1. Project Name", "Project Name:"
        # Take lines that look like titles (short-ish, may have bullet)
        cleaned = re.sub(r'^[\s•\-\*\d.)+]+', '', line).strip()
        if cleaned and len(cleaned) < 150:
            # Check if it looks like a title (not a description paragraph)
            if len(cleaned.split()) <= 20 or cleaned.endswith(':') or cleaned.endswith(')'):
                projects.append(cleaned)

    return projects if projects else [projects_text[:100]]


def _extract_cert_names(certs_text: str) -> list[str]:
    """Extract certification names."""
    lines = certs_text.split("\n")
    certs: list[str] = []
    for line in lines:
        cleaned = re.sub(r'^[\s•\-\*\d.)+]+', '', line).strip()
        if cleaned and len(cleaned) > 3:
            certs.append(cleaned)
    return certs


def _extract_experience_roles(exp_text: str) -> list[str]:
    """Extract role/company entries from experience section."""
    lines = exp_text.split("\n")
    roles: list[str] = []
    for line in lines:
        cleaned = re.sub(r'^[\s•\-\*\d.)+]+', '', line).strip()
        if cleaned and len(cleaned) > 5 and len(cleaned) < 150:
            roles.append(cleaned)
    return roles


# ──────────────────────────────────────────────
#  Main scoring function
# ──────────────────────────────────────────────

def score_proficiency(
    skill: str,
    resume_text: str,
    resume_sections: dict | None = None,
) -> SkillEvidence:
    """
    Calculate evidence-based proficiency for a skill against resume text.

    Args:
        skill: The skill to score.
        resume_text: Full raw resume text.
        resume_sections: Optional pre-parsed sections from LLM extraction.

    Returns:
        SkillEvidence with score, level, and source tags.
    """
    evidence = SkillEvidence()

    # Parse sections from raw text (fallback if LLM sections not provided)
    sections = _extract_sections(resume_text)

    # ── Profile/Objective/Summary section ── (low weight: +1)
    profile_text = sections.get("objective", "")
    if _skill_mentioned_in(profile_text, skill):
        evidence.in_profile_section = True
        evidence.raw_score += 1

    # ── Skills section ──
    skills_text = sections.get("skills", "")
    if _skill_mentioned_in(skills_text, skill):
        evidence.in_skills_section = True
        evidence.raw_score += 2

    # ── Projects section ──
    projects_text = sections.get("projects", "")
    if projects_text:
        project_names = _extract_project_names(projects_text)
        project_count = 0
        for proj_name in project_names:
            # Check if skill is mentioned in the project name/description
            # Also check a chunk of text around it
            if _skill_mentioned_in(proj_name, skill):
                evidence.projects.append(proj_name[:80])
                project_count += 1

        if project_count > 0:
            evidence.raw_score += 4  # First project
            if project_count > 1:
                evidence.raw_score += 3 * (project_count - 1)  # Additional projects

    # ── Certifications section ──
    certs_text = sections.get("certifications", "")
    if certs_text:
        cert_names = _extract_cert_names(certs_text)
        for cert in cert_names:
            if _skill_mentioned_in(cert, skill):
                evidence.certifications.append(cert[:80])
                evidence.raw_score += 3

    # ── Experience section ──
    exp_text = sections.get("experience", "")
    if _skill_mentioned_in(exp_text, skill):
        roles = _extract_experience_roles(exp_text)
        for role in roles:
            if _skill_mentioned_in(role, skill):
                evidence.experience.append(role[:80])
        if not evidence.experience and exp_text:
            evidence.experience.append("(mentioned in experience)")
        evidence.raw_score += 5

    # ── Achievements section ──
    achievements_text = sections.get("achievements", "")
    if _skill_mentioned_in(achievements_text, skill):
        evidence.achievements.append("(mentioned in achievements)")
        evidence.raw_score += 2

    # ── Also check LLM-provided resume_sections if available ──
    if resume_sections:
        _enrich_from_llm_sections(evidence, skill, resume_sections)

    # ── Determine level ──
    score = evidence.raw_score
    if score <= 0:
        evidence.level = "unknown"
    elif score <= 2:
        evidence.level = "beginner"
    elif score <= 5:
        evidence.level = "basic"
    elif score <= 8:
        evidence.level = "intermediate"
    elif score <= 12:
        evidence.level = "advanced"
    else:
        evidence.level = "expert"

    # Cap profile-only skills at beginner — mentioned in summary but
    # no concrete evidence from skills/projects/experience/certs
    if (
        evidence.in_profile_section
        and not evidence.in_skills_section
        and not evidence.projects
        and not evidence.experience
        and not evidence.certifications
        and not evidence.achievements
    ):
        evidence.level = "beginner"

    return evidence


def _enrich_from_llm_sections(
    evidence: SkillEvidence,
    skill: str,
    llm_sections: dict,
) -> None:
    """
    Supplement regex-based evidence with LLM-extracted section data.

    This handles cases where the regex missed something the LLM caught.
    Avoids double-counting by checking existing evidence.
    """
    # Check LLM profile section
    llm_profile_skills = llm_sections.get("profile", [])
    if isinstance(llm_profile_skills, list):
        for ps in llm_profile_skills:
            if isinstance(ps, str) and are_semantically_equivalent(ps, skill):
                if not evidence.in_profile_section:
                    evidence.in_profile_section = True
                    evidence.raw_score += 1
                break  # Only count once

    # Check LLM projects
    llm_projects = llm_sections.get("projects", [])
    for proj in llm_projects:
        if isinstance(proj, dict):
            proj_name = proj.get("name", "")
            inferred = proj.get("inferred_skills", [])
            # Check if this skill appears in the project's inferred skills
            for inf_skill in inferred:
                if are_semantically_equivalent(inf_skill, skill):
                    # Only add if not already tracked
                    if proj_name and proj_name[:80] not in evidence.projects:
                        evidence.projects.append(proj_name[:80])
                        evidence.raw_score += 4 if len(evidence.projects) == 1 else 3

    # Check LLM certifications
    llm_certs = llm_sections.get("certifications", [])
    for cert in llm_certs:
        if isinstance(cert, dict):
            cert_name = cert.get("name", "")
            inferred = cert.get("inferred_skills", [])
            for inf_skill in inferred:
                if are_semantically_equivalent(inf_skill, skill):
                    if cert_name and cert_name[:80] not in evidence.certifications:
                        evidence.certifications.append(cert_name[:80])
                        evidence.raw_score += 3

    # Check LLM experience
    llm_exp = llm_sections.get("experience", [])
    for exp in llm_exp:
        if isinstance(exp, dict):
            role = exp.get("role", "")
            inferred = exp.get("inferred_skills", [])
            for inf_skill in inferred:
                if are_semantically_equivalent(inf_skill, skill):
                    if role and role[:80] not in evidence.experience:
                        evidence.experience.append(role[:80])
                        evidence.raw_score += 5


def score_all_skills(
    skills: list[str],
    resume_text: str,
    resume_sections: dict | None = None,
) -> dict[str, SkillEvidence]:
    """
    Score proficiency for a list of skills.

    Returns dict mapping skill name → SkillEvidence.
    """
    results: dict[str, SkillEvidence] = {}
    for skill in skills:
        results[skill] = score_proficiency(skill, resume_text, resume_sections)
    return results
