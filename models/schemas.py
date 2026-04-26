"""
Pydantic schemas for request/response validation across all endpoints.
Every LLM output is validated against these models before being returned.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ──────────────────────────────────────────────
#  Enums
# ──────────────────────────────────────────────

class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class GapPriority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# ──────────────────────────────────────────────
#  Skill Extraction & Matching
# ──────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    job_description: str = Field(..., min_length=20, description="Full job description text")
    resume: str = Field(..., min_length=20, description="Full resume text")


class ExtractedSkills(BaseModel):
    """Schema for LLM skill-extraction output."""
    jd_skills: list[str] = Field(default_factory=list, description="Skills extracted from the job description")
    resume_skills: list[str] = Field(default_factory=list, description="Skills extracted from the resume")


class ExtractedSkillsDetailed(BaseModel):
    """Richer schema for LLM skill-extraction with section annotations."""
    jd_skills: list[str] = Field(default_factory=list)
    resume_skills: list[str] = Field(default_factory=list)
    resume_sections: dict = Field(default_factory=dict, description="Section-annotated skills from the resume")


class SkillMatch(BaseModel):
    skill: str
    found_in_resume: bool
    proficiency_estimate: str = Field(
        default="unknown",
        description="Estimated proficiency: beginner | basic | intermediate | advanced | expert | unknown",
    )
    proficiency_score: int = Field(default=0, description="Raw numeric proficiency score")
    evidence_sources: list[str] = Field(default_factory=list, description="Evidence source tags")
    matched_via: str = Field(default="", description="How the match was made: exact | synonym | inferred")


class AnalyzeResponse(BaseModel):
    jd_skills: list[str]
    resume_skills: list[str]
    matched_skills: list[SkillMatch]
    match_percentage: float = Field(ge=0, le=100)
    missing_skills: list[str]
    extra_skills: list[str] = Field(default_factory=list, description="Resume skills not in JD")
    proficiency_summary: dict[str, str] = Field(default_factory=dict, description="Skill → proficiency level")


# ──────────────────────────────────────────────
#  Interview / Question Generation
# ──────────────────────────────────────────────

class GenerateQuestionsRequest(BaseModel):
    skill: str = Field(..., min_length=1, description="Skill to generate questions for")
    difficulty: Difficulty = Difficulty.MEDIUM
    count: int = Field(default=3, ge=1, le=10)
    context: Optional[str] = Field(default=None, description="Optional JD context for relevance")


class InterviewQuestion(BaseModel):
    question: str
    difficulty: str
    skill: str
    expected_answer_points: list[str] = Field(default_factory=list)


class GenerateQuestionsResponse(BaseModel):
    skill: str
    difficulty: str
    questions: list[InterviewQuestion]


# ──────────────────────────────────────────────
#  Evaluation
# ──────────────────────────────────────────────

class EvaluateRequest(BaseModel):
    question: str = Field(..., min_length=5)
    answer: str = Field(..., min_length=1)
    skill: str = Field(..., min_length=1)
    difficulty: Difficulty = Difficulty.MEDIUM


class EvaluationResult(BaseModel):
    conceptual_understanding: int = Field(ge=0, le=10)
    practical_knowledge: int = Field(ge=0, le=10)
    clarity: int = Field(ge=0, le=10)
    confidence: int = Field(ge=0, le=10)
    final_score: float = Field(ge=0, le=10)
    feedback: str
    correct_answer: str

    @field_validator("final_score", mode="before")
    @classmethod
    def round_score(cls, v: float) -> float:
        return round(float(v), 2)


class EvaluateResponse(BaseModel):
    skill: str
    difficulty: str
    evaluation: EvaluationResult
    next_difficulty: str = Field(description="Adaptive difficulty for the next question")


# ──────────────────────────────────────────────
#  Gap Analysis
# ──────────────────────────────────────────────

class GapAnalysisRequest(BaseModel):
    required_skills: list[str] = Field(..., min_length=1)
    scores: dict[str, float] = Field(
        ...,
        description="Mapping of skill name → evaluation score (0-10)",
    )


class SkillGap(BaseModel):
    skill: str
    score: float = Field(ge=0, le=10)
    priority: GapPriority
    is_required: bool = True
    recommendation: str = ""


class GapAnalysisResponse(BaseModel):
    gaps: list[SkillGap]
    high_priority_count: int
    medium_priority_count: int
    low_priority_count: int
    overall_readiness: float = Field(ge=0, le=100, description="Percentage readiness for the role")


# ──────────────────────────────────────────────
#  Learning Plan
# ──────────────────────────────────────────────

class LearningPlanRequest(BaseModel):
    skill_gaps: list[SkillGap]
    available_hours_per_day: float = Field(default=2.0, ge=0.5, le=12)
    days_per_week: int = Field(default=7, ge=1, le=7)
    target_weeks: int = Field(default=8, ge=1, le=52)


class LearningResource(BaseModel):
    title: str
    type: str = Field(description="course | book | tutorial | practice | documentation")
    url: str = ""
    estimated_hours: float = 0


class LearningTopic(BaseModel):
    topic: str
    sub_skills: list[str] = Field(default_factory=list)
    week: int
    daily_hours: float
    difficulty_weight: int = Field(default=5, ge=1, le=10, description="Weight/difficulty of the topic (1-10)")
    resources: list[LearningResource] = Field(default_factory=list)
    milestones: list[str] = Field(default_factory=list)


class SkillLearningPlan(BaseModel):
    skill: str
    covers_skills: list[str] = Field(default_factory=list)
    priority: str
    current_score: float
    target_score: float = 8.0
    duration_weeks: int
    topics: list[LearningTopic] = Field(default_factory=list)
    adjacent_skills: list[str] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list, description="List of prerequisite skill names")


class DayScheduleItem(BaseModel):
    day: int
    topic: str
    hours: float


class LearningPlanResponse(BaseModel):
    total_duration_weeks: int
    daily_hours: float
    plans: list[SkillLearningPlan]
    day_schedule: list[DayScheduleItem] = Field(default_factory=list)
    summary: str = ""
