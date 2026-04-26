# 📥 Sample Input & Output

This document provides realistic examples of requests and responses for the AI Interview Agent's API.

> [!NOTE]
> These examples are for **structural reference only**. The actual quality, accuracy, and depth of the output depend on several factors:
> 1. The **LLM model** being used (Gemini, LLaMA, etc.).
> 2. The **input text** provided (JD and Resume).
> 3. The **system prompts** configured in the backend.
> 4. The interaction between the **LLM and the deterministic backend logic** used for matching and scoring.

---

## 🔍 `POST /analyze`
**Endpoint**: `http://localhost:8000/analyze`  
**Purpose**: Extracts skills from a Job Description and Resume, matches them using a 5-layer pipeline, and scores proficiency based on evidence.

### Sample Request
```json
{
  "job_description": "We are looking for a Senior Python Developer. Requirements: Python 3.10+, FastAPI, Docker, and experience with PostgreSQL. Knowledge of Machine Learning (scikit-learn) is a plus.",
  "resume": "Experienced Backend Engineer with 6 years in software development. Expert in Python and Flask. Integrated Docker into CI/CD pipelines. Managed complex SQL databases. Certified AWS Developer."
}
```

### Sample Response
```json
{
  "jd_skills": ["Python", "FastAPI", "Docker", "PostgreSQL", "Machine Learning", "scikit-learn"],
  "resume_skills": ["Python", "Flask", "Docker", "SQL", "CI/CD", "AWS"],
  "matched_skills": [
    {
      "skill": "Python",
      "found_in_resume": true,
      "proficiency_estimate": "expert",
      "proficiency_score": 14,
      "evidence_sources": ["Exp (6 years)", "Skills (Python)"],
      "matched_via": "exact"
    },
    {
      "skill": "Docker",
      "found_in_resume": true,
      "proficiency_estimate": "intermediate",
      "proficiency_score": 7,
      "evidence_sources": ["Project (Integrated Docker)"],
      "matched_via": "exact"
    },
    {
      "skill": "PostgreSQL",
      "found_in_resume": true,
      "proficiency_estimate": "basic",
      "proficiency_score": 4,
      "evidence_sources": ["Exp (SQL databases)"],
      "matched_via": "synonym"
    },
    {
      "skill": "FastAPI",
      "found_in_resume": false,
      "proficiency_estimate": "unknown",
      "proficiency_score": 0,
      "evidence_sources": [],
      "matched_via": ""
    }
  ],
  "match_percentage": 75.0,
  "missing_skills": ["FastAPI", "Machine Learning"],
  "extra_skills": ["AWS", "CI/CD"],
  "proficiency_summary": {
    "Python": "expert",
    "Docker": "intermediate",
    "PostgreSQL": "basic"
  }
}
```

---

## ❓ `POST /generate-questions`
**Endpoint**: `http://localhost:8000/generate-questions`  
**Purpose**: Generates difficulty-adaptive interview questions for a specific skill.

### Sample Request
```json
{
  "skill": "Python",
  "difficulty": "medium",
  "count": 2,
  "context": "Senior Backend role with focus on performance."
}
```

### Sample Response
```json
{
  "skill": "Python",
  "difficulty": "medium",
  "questions": [
    {
      "question": "Explain the difference between deep copy and shallow copy in Python, and when would you use each?",
      "difficulty": "medium",
      "skill": "Python",
      "expected_answer_points": ["ID vs value", "Nested objects", "copy module"]
    },
    {
      "question": "How do you manage memory in Python, particularly regarding the Global Interpreter Lock (GIL)?",
      "difficulty": "medium",
      "skill": "Python",
      "expected_answer_points": ["Ref counting", "GC", "Multi-threading impact"]
    }
  ]
}
```

---

## 📝 `POST /evaluate`
**Endpoint**: `http://localhost:8000/evaluate`  
**Purpose**: Scores a candidate's answer across 4 dimensions and recommends the next difficulty level.

### Sample Request
```json
{
  "question": "Explain the difference between deep copy and shallow copy.",
  "answer": "Shallow copy creates a new object but references the nested ones, while deep copy clones everything including children.",
  "skill": "Python",
  "difficulty": "medium"
}
```

### Sample Response
```json
{
  "skill": "Python",
  "difficulty": "medium",
  "evaluation": {
    "conceptual_understanding": 9,
    "practical_knowledge": 8,
    "clarity": 10,
    "confidence": 7,
    "final_score": 8.6,
    "feedback": "Correct definition. Good clarity. Could mention the 'copy' module for a perfect score.",
    "correct_answer": "A shallow copy constructs a new compound object and then inserts references into it to the objects found in the original..."
  },
  "next_difficulty": "hard"
}
```

---

## 📊 `POST /gap-analysis`
**Endpoint**: `http://localhost:8000/gap-analysis`  
**Purpose**: Categorizes skill gaps based on evaluation scores and JD requirements.

### Sample Request
```json
{
  "required_skills": ["Python", "FastAPI", "Docker"],
  "scores": {
    "Python": 8.6,
    "Docker": 4.2
  }
}
```

### Sample Response
```json
{
  "gaps": [
    {
      "skill": "FastAPI",
      "score": 0.0,
      "priority": "HIGH",
      "is_required": true,
      "recommendation": "Urgent: No evidence found for FastAPI. Focus on routing and Pydantic models."
    },
    {
      "skill": "Docker",
      "score": 4.2,
      "priority": "MEDIUM",
      "is_required": true,
      "recommendation": "Improve understanding of Docker Compose and multi-stage builds."
    },
    {
      "skill": "Python",
      "score": 8.6,
      "priority": "LOW",
      "is_required": true,
      "recommendation": "Strong performance. Explore advanced metaprogramming."
    }
  ],
  "high_priority_count": 1,
  "medium_priority_count": 1,
  "low_priority_count": 1,
  "overall_readiness": 42.67
}
```

---

## 📅 `POST /learning-plan`
**Endpoint**: `http://localhost:8000/learning-plan`  
**Purpose**: Generates a week-by-week learning roadmap with resources and a daily schedule.

### Sample Request
```json
{
  "skill_gaps": [
    { "skill": "FastAPI", "score": 0.0, "priority": "HIGH" },
    { "skill": "Docker", "score": 4.2, "priority": "MEDIUM" }
  ],
  "available_hours_per_day": 2,
  "target_weeks": 4
}
```

### Sample Response
```json
{
  "total_duration_weeks": 4,
  "daily_hours": 2,
  "plans": [
    {
      "skill": "FastAPI",
      "priority": "HIGH",
      "current_score": 0.0,
      "target_score": 8.0,
      "duration_weeks": 2,
      "topics": [
        {
          "topic": "FastAPI Fundamentals",
          "week": 1,
          "daily_hours": 2,
          "resources": [
            { "title": "FastAPI Official Tutorial", "type": "documentation", "url": "https://fastapi.tiangolo.com/" }
          ],
          "milestones": ["Build a CRUD API"]
        }
      ]
    }
  ],
  "day_schedule": [
    { "day": 1, "topic": "FastAPI Fundamentals", "hours": 2 },
    { "day": 2, "topic": "FastAPI Fundamentals", "hours": 2 }
  ],
  "summary": "This 4-week plan focuses on closing your high-priority gap in FastAPI first, followed by Docker stabilization."
}
```
