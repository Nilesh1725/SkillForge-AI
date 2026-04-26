# 🧠 Logic & Data Flow Documentation

Complete breakdown of how data flows through each section of the AI Interview Agent, with emphasis on the skill matching pipeline.

---

## Table of Contents

- [Overall Request Flow](#overall-request-flow)
- [1. Skill Extraction (`POST /analyze` — Phase 1)](#1-skill-extraction)
- [2. Skill Matching (`POST /analyze` — Phase 2)](#2-skill-matching)
- [3. Proficiency Scoring](#3-proficiency-scoring)
- [4. Extra/Missing Skill Calculation (`POST /analyze` — Phase 3)](#4-extramissing-skill-calculation)
- [5. Interview Questions (`POST /generate-questions`)](#5-interview-questions)
- [6. Answer Evaluation (`POST /evaluate`)](#6-answer-evaluation)
- [7. Gap Analysis (`POST /gap-analysis`)](#7-gap-analysis)
- [8. Learning Plan (`POST /learning-plan`)](#8-learning-plan)
- [Skill Mappings Architecture](#skill-mappings-architecture)

---

## Overall Request Flow

```
User Input (JD + Resume)
        │
        ▼
┌──────────────────┐
│  /analyze         │ ──► Skill Extraction (LLM)
│                   │ ──► Skill Matching (deterministic 5-layer)
│                   │ ──► Proficiency Scoring (evidence-based)
│                   │ ──► Extra/Missing calculation
└──────────────────┘
        │
        ▼
┌──────────────────┐
│  /generate-       │ ──► Generate adaptive interview questions
│  questions        │     based on matched skills + proficiency
└──────────────────┘
        │
        ▼
┌──────────────────┐
│  /evaluate        │ ──► Score candidate answers (4 dimensions)
│                   │ ──► Determine next difficulty level
└──────────────────┘
        │
        ▼
┌──────────────────┐
│  /gap-analysis    │ ──► Categorize skill gaps (HIGH/MED/LOW)
└──────────────────┘
        │
        ▼
┌──────────────────┐
│  /learning-plan   │ ──► Generate personalized learning roadmap
└──────────────────┘
```

---

## 1. Skill Extraction

**File:** `services/skill_extractor.py`
**Prompt:** `utils/prompts.py → SKILL_EXTRACTION_PROMPT`

### Input
```
job_description: str  (raw JD text)
resume: str           (raw resume text)
```

### Flow

```
JD + Resume text
      │
      ▼
┌─────────────────────────┐
│  LLM (Gemini / HF)     │
│                         │
│  Prompt instructs LLM   │
│  to scan ALL sections:  │
│  • Profile/Summary      │
│  • Skills               │
│  • Projects             │
│  • Certifications       │
│  • Experience           │
│  • Achievements         │
└─────────────────────────┘
      │
      ▼
┌─────────────────────────┐
│  Raw JSON Response      │
│  {                      │
│    jd_skills: [...],    │
│    resume_skills: [...],│
│    resume_sections: {   │
│      profile: [...],    │
│      skills: [...],     │
│      projects: [{       │
│        name, desc,      │
│        inferred_skills  │
│      }],                │
│      experience: [...], │
│      ...                │
│    }                    │
│  }                      │
└─────────────────────────┘
      │
      ▼
┌─────────────────────────┐
│  Section Merging        │
│                         │
│  For each section:      │
│  profile → skills       │
│  projects.inferred →    │
│    skills               │
│  experience.inferred →  │
│    skills               │
│  certs.inferred →       │
│    skills               │
│                         │
│  Dedup by lowercase     │
└─────────────────────────┘
      │
      ▼
Output: ExtractedSkillsDetailed {
  jd_skills, resume_skills, resume_sections
}
```

### Key Rules
- LLM infers **both tech and soft/process skills** from context (e.g., "Generated reports" → Reporting)
- Profile/Summary skills are extracted but have lower proficiency weight
- All section-inferred skills are merged into `resume_skills` (deduplicated by lowercase)

---

## 2. Skill Matching

**File:** `services/skill_matcher.py`

### Input
```
jd_skills: list[str]            (from extraction)
resume_skills: list[str]        (from extraction)
resume_text: str                (raw resume text)
resume_sections: dict           (LLM-parsed sections)
```

### 5-Layer Matching Pipeline

```
For each JD skill:
      │
      ▼
┌─── Layer 1: EXACT MATCH ─────────────────────┐
│  jd_skill.lower() in resume_skills_lower?     │
│  "Python" == "python" ✅                       │
│  If YES → found=True, method="exact"          │
└───────────────────────────────────────────────┘
      │ (if not found)
      ▼
┌─── Layer 2: SYNONYM MATCH ────────────────────┐
│  normalize_skill(jd) == normalize_skill(res)?  │
│  "MySQL" → canonical "SQL" == "SQL" ✅         │
│  Uses SKILL_SYNONYMS reverse index (O(1))     │
│  If YES → found=True, method="synonym"        │
└───────────────────────────────────────────────┘
      │ (if not found)
      ▼
┌─── Layer 3: SUB-SKILL HIERARCHY ──────────────┐
│  Is any resume skill a sub-skill of JD skill? │
│  JD: "Data Analysis", Resume: "Pandas" ✅      │
│  Uses SKILL_HIERARCHY map                     │
│  Even if already found, marks sub-skills as   │
│  "used" to prevent false extras               │
│  If YES → found=True, method="sub-skill"      │
└───────────────────────────────────────────────┘
      │ (if not found)
      ▼
┌─── Layer 4: INFERRED FROM SECTIONS ───────────┐
│  Check resume_sections (projects, certs,      │
│  experience, skills) for semantically         │
│  equivalent inferred skills                   │
│  Uses are_semantically_equivalent()           │
│  If YES → found=True, method="inferred"       │
└───────────────────────────────────────────────┘
      │ (if not found)
      ▼
┌─── Layer 5: CONTEXTUAL (projects only) ───────┐
│  Check project names + descriptions for       │
│  contextual keywords from SEMANTIC_RELATIONS  │
│  "Tumor Classification" → "Predictive         │
│   Analysis" ✅ (keyword: "classification")     │
│  SCOPED TO PROJECTS to avoid false positives  │
│  If YES → found=True, method="contextual"     │
└───────────────────────────────────────────────┘
      │
      ▼
┌─── PROFICIENCY ENGINE FALLBACK ───────────────┐
│  If still not found but proficiency engine    │
│  found evidence (raw_score > 0),             │
│  trust the evidence → found=True             │
└───────────────────────────────────────────────┘
```

### Used Skills Tracking

Throughout matching, a `used_skills: set[str]` tracks which resume skills were consumed:

| Event | What gets added to `used_skills` |
|-------|----------------------------------|
| Exact/synonym match | The matched resume skill (lowercase) |
| Sub-skill match | All matching sub-skills |
| Already-found + sub-skills exist | Sub-skills still marked as used |
| JD skill itself found | JD skill lowercase added |

This set is passed back to the caller to correctly compute extra skills.

---

## 3. Proficiency Scoring

**File:** `services/proficiency_engine.py`

### Scoring Weights

| Section | Weight | Notes |
|---------|--------|-------|
| Profile/Summary | +1 | Claimed without evidence — lowest weight |
| Skills section | +2 | Explicitly listed |
| First Project | +4 | Strongest hands-on evidence |
| Additional Projects | +3 each | Cumulative |
| Certification | +3 | Formal validation |
| Experience | +5 | Professional usage — highest weight |
| Achievement | +2 | Recognition |

### Level Thresholds

| Score | Level |
|-------|-------|
| 0 | unknown |
| 1–2 | beginner |
| 3–5 | basic |
| 6–8 | intermediate |
| 9–12 | advanced |
| 13+ | expert |

### Profile-Only Cap

If a skill is found **only** in the Profile/Summary section (no evidence from skills, projects, experience, or certs), the proficiency is **capped at "beginner"** regardless of the numeric score.

### Two-Phase Scanning

```
Phase 1: Regex-based section detection
  └─ Parse raw resume text into sections using regex patterns
  └─ Search for skill mentions in each section
  └─ Accumulate evidence + score

Phase 2: LLM section enrichment
  └─ Check LLM-provided resume_sections
  └─ Supplement regex misses
  └─ Avoid double-counting existing evidence
```

---

## 4. Extra/Missing Skill Calculation

**File:** `routes/analyze.py`

### Missing Skills
```python
missing = [m.skill for m in matched if not m.found_in_resume]
```
Simply: JD skills that were NOT matched by any layer.

### Extra Skills

```
For each resume_skill:
      │
      ▼
  Is canonical form in jd_canonicals? ──► SKIP (it's a JD skill)
      │
  Is lowercase in used_skills? ──► SKIP (consumed by matching)
      │
  Already listed? ──► SKIP (dedup)
      │
  Otherwise ──► ADD to extra_skills
```

### Why This Matters

Without `used_skills` tracking, a skill like "Pandas" would appear as "extra" even though it was consumed to satisfy the "Data Analysis" JD requirement via sub-skill hierarchy matching.

---

## 5. Interview Questions

**File:** `services/question_generator.py`
**Endpoint:** `POST /generate-questions`

### Flow
```
Input: skill, difficulty, count, context
      │
      ▼
  Build prompt with skill + difficulty + optional JD context
      │
      ▼
  LLM generates questions with expected_answer_points
      │
      ▼
  Validate against InterviewQuestion schema
      │
      ▼
Output: list[InterviewQuestion]
```

---

## 6. Answer Evaluation

**File:** `services/evaluator.py`
**Endpoint:** `POST /evaluate`

### Scoring Dimensions
```
┌─────────────────────────────┐
│  Conceptual Understanding   │  30% weight
│  Practical Knowledge        │  30% weight
│  Clarity                    │  20% weight
│  Confidence                 │  20% weight
│  ─────────────────────────  │
│  final_score = weighted avg │
└─────────────────────────────┘
```

### Adaptive Difficulty
```
Score > 7  →  Next: HARD
Score < 4  →  Next: EASY
Otherwise  →  Next: MEDIUM
```

### Critical Rule
If candidate says "I don't know" or gives empty/irrelevant answer → ALL dimensions score **0**.

---

## 7. Gap Analysis

**File:** `services/gap_analysis.py`
**Endpoint:** `POST /gap-analysis`

### Priority Logic
```
Score < 5  AND required  →  HIGH priority
Score ≤ 7  AND required  →  MEDIUM priority
Score > 7  OR not required →  LOW priority
```

### Flow
```
Input: required_skills + scores
      │
      ▼
  Validate & clamp scores (0-10)
      │
      ▼
  LLM generates recommendations for each gap
      │
      ▼
  Deterministic priority assignment (not LLM-dependent)
      │
      ▼
  Calculate overall_readiness = avg(required_scores) / 10 * 100
      │
      ▼
Output: GapAnalysisResponse (sorted: HIGH → MED → LOW)
```

---

## 8. Learning Plan

**File:** `services/learning_plan.py`
**Endpoint:** `POST /learning-plan`

### Flow
```
Input: skill_gaps + available_hours + target_weeks
      │
      ▼
  Group related skills (semantic clustering)
      │
      ▼
  LLM generates topic-by-topic roadmap with:
  • Resources (courses, docs, tutorials)
  • Milestones (mini-projects, practical tasks)
  • Prerequisites (dependency ordering)
  • Adjacent skills
      │
      ▼
  Build day-by-day schedule based on:
  • difficulty_weight of each topic
  • available_hours_per_day
  • priority ordering (HIGH first)
      │
      ▼
Output: LearningPlanResponse with plans + day_schedule
```

---

## Skill Mappings Architecture

**File:** `services/skill_mappings.py`

Three independent mapping systems, each serving a different purpose:

### 1. SKILL_SYNONYMS (Strict Equivalence)

```
"MySQL" ──normalize──► "SQL"          (same skill, different name)
"sklearn" ──normalize──► "Scikit-Learn" (same library, alias)
```

- **Purpose:** Layer 1–2 matching (exact + synonym)
- **Reverse index:** O(1) alias → canonical lookup
- **Strictness:** HIGH — these are true equivalences

### 2. SKILL_HIERARCHY (Parent ← Child)

```
"Data Analysis" ──children──► ["pandas", "numpy", "sql", "excel", ...]
"Machine Learning" ──children──► ["scikit-learn", "xgboost", ...]
```

- **Purpose:** Layer 3 matching + used_skills tracking
- **Direction:** Child resume skill satisfies parent JD skill
- **Also:** Marks sub-skills as "used" to prevent false extras

### 3. SEMANTIC_RELATIONS (Contextual Keywords)

```
"Predictive Analysis" ──keywords──► ["classification", "regression", "forecasting", ...]
"Reporting" ──keywords──► ["reports", "insights", "dashboards", ...]
```

- **Purpose:** Layer 5 matching (contextual, projects only)
- **Scope:** ONLY checked against project names/descriptions
- **Strictness:** LOW — keyword presence in context = match
- **Why projects only:** To avoid false positives from unrelated text

### Comparison Table

| Map | Strictness | Scope | Use Case |
|-----|-----------|-------|----------|
| SKILL_SYNONYMS | Strict | All resume skills | "MySQL" = "SQL" |
| SKILL_HIERARCHY | Medium | Resume skills → JD parent | "Pandas" satisfies "Data Analysis" |
| SEMANTIC_RELATIONS | Loose | Project descriptions only | "tumor classification" → "Predictive Analysis" |
