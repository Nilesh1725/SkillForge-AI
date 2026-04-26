"""
Centralized prompt templates for all LLM interactions.

Every prompt enforces JSON-only output with explicit examples to maximise
structured-output compliance from LLaMA / Mixtral models.
"""

# ──────────────────────────────────────────────
#  Skill Extraction
# ──────────────────────────────────────────────

SKILL_EXTRACTION_PROMPT = """You are an expert HR analyst. Extract technical and soft skills from the following Job Description and Resume.

IMPORTANT: Scan ALL sections of the resume, not just the "Skills" section.
Extract skills from: Profile/Objective/Summary, Skills, Projects, Certifications, Experience, Achievements, Tools.

## Skill Inference Rules

When scanning Projects, infer skills ONLY when clearly justified by the project name or description.
Examples of valid inference:
- "Brain Tumor Classification using ML" => Machine Learning, Classification, Predictive Analysis
- "Data Analysis Dashboard (Python + Excel)" => Python, Excel, Data Visualization
- "Generated insights and reports for decision-making" => Reporting, Data Analysis
Do NOT hallucinate skills that are not supported by the text.

When scanning Experience, infer BOTH technical AND soft/process skills from bullet points:
- "Generated insights and reports for decision-making" => Reporting, Data Analysis
- "Led a team of 5 engineers" => Project Management, Communication
- "Collaborated with stakeholders to gather requirements" => Communication, Problem Solving
- "Built and maintained dashboards" => Data Visualization, Reporting

When scanning Profile/Objective/Summary:
- Extract any skills mentioned (e.g., "Aspiring data scientist with expertise in Python and ML")
- These are typically claimed skills without strong evidence, so mark them separately

### Job Description:
{job_description}

### Resume:
{resume}

Return ONLY valid JSON in exactly this format -- no explanation, no markdown fences, no extra text:

{{
  "jd_skills": ["Python", "SQL", "Excel", "Data Visualization", "Reporting"],
  "resume_skills": ["Python", "Pandas", "SQL", "Machine Learning", "Reporting"],
  "resume_sections": {{
    "profile": ["Python", "Machine Learning"],
    "skills": ["Python", "SQL"],
    "projects": [
      {{"name": "Brain Tumor Classification using ML", "description": "Built a classifier to predict tumor types", "inferred_skills": ["Machine Learning", "Classification", "Predictive Analysis"]}},
      {{"name": "Data Analysis Dashboard (Python + Excel)", "description": "Generated insights and reports for decision-making", "inferred_skills": ["Python", "Excel", "Data Visualization", "Reporting", "Data Analysis"]}}
    ],
    "certifications": [
      {{"name": "AWS Cloud Practitioner", "inferred_skills": ["AWS", "Cloud Computing"]}}
    ],
    "experience": [
      {{"role": "Data Analyst at XYZ", "inferred_skills": ["Data Analysis", "SQL", "Reporting"]}}
    ],
    "achievements": []
  }}
}}

Rules:
- jd_skills: ALL skills required by the job description (in requirements, responsibilities, preferred or qualifications sections)
- resume_skills: ALL unique skills found across ALL resume sections (deduplicated) — include soft skills and process skills too
- resume_sections: section-by-section breakdown of WHERE each skill was found
- profile: skills mentioned in Profile/Objective/Summary section (list of strings)
- projects: MUST include both "name" and "description" fields (use the project's bullet points or description text as description)
- Infer soft skills and process skills (Reporting, Communication, Problem Solving) from experience/project descriptions — not just tech skills
- If a section does not exist in the resume, use an empty list []
- Return ONLY the JSON object. Nothing else."""


# ──────────────────────────────────────────────
#  Skill Matching
# ──────────────────────────────────────────────

SKILL_MATCHING_PROMPT = """You are an expert skill matcher. Compare the following JD skills against resume skills and determine matches.

### JD Skills:
{jd_skills}

### Resume Skills:
{resume_skills}

For each JD skill, determine:
1. Whether it is found in the resume (exact match OR semantic equivalent)
   - Use semantic skill mapping (e.g., "NumPy + Pandas" => "Data Analysis")
2. Estimated proficiency based on resume context: "beginner", "intermediate", "advanced", or "unknown"
   - IMPORTANT: If a skill is inferred indirectly (e.g., from tools like NumPy/Pandas) but no project, experience, or proof is explicitly present, set proficiency to "beginner" or "unknown". Do NOT assign intermediate or advanced.

Return ONLY valid JSON -- no explanation, no markdown:

{{
  "matches": [
    {{"skill": "Python", "found_in_resume": true, "proficiency_estimate": "advanced"}},
    {{"skill": "Docker", "found_in_resume": false, "proficiency_estimate": "unknown"}}
  ]
}}

Return ONLY the JSON object."""


# ──────────────────────────────────────────────
#  Question Generation
# ──────────────────────────────────────────────

QUESTION_GENERATION_PROMPT = """You are a senior technical interviewer. Generate {count} interview questions for the skill "{skill}" at {difficulty} difficulty level.

{context_section}

Each question must test real-world knowledge. Include expected answer points.

Return ONLY valid JSON -- no explanation, no markdown:

{{
  "questions": [
    {{
      "question": "Explain how Python's GIL affects multi-threaded applications.",
      "difficulty": "{difficulty}",
      "skill": "{skill}",
      "expected_answer_points": [
        "GIL prevents true parallel execution of Python bytecode",
        "I/O-bound tasks can still benefit from threading",
        "Use multiprocessing for CPU-bound tasks"
      ]
    }}
  ]
}}

Generate exactly {count} questions. Return ONLY the JSON object."""


# ──────────────────────────────────────────────
#  Evaluation
# ──────────────────────────────────────────────

EVALUATION_PROMPT = """You are an expert technical evaluator. Score the candidate's answer to the following interview question.

### Skill: {skill}
### Difficulty: {difficulty}
### Question: {question}
### Candidate's Answer: {answer}

Score each dimension from 0 to 10:
- conceptual_understanding: Does the candidate understand the core concepts?
- practical_knowledge: Can they apply it in real-world scenarios?
- clarity: Is the answer well-structured and clear?
- confidence: Does the answer demonstrate confidence and depth?
- final_score: Weighted average (concept 30%, practical 30%, clarity 20%, confidence 20%)

CRITICAL EVALUATION RULE:
If the candidate answers "I don't know", gives an evasive answer, or provides an empty/irrelevant response, you MUST score ALL dimensions (including clarity and confidence) as 0.

Also provide:
- feedback: Constructive feedback for the candidate (short and concise)
- correct_answer: A brief, correct model answer

Return ONLY valid JSON -- no explanation, no markdown:

{{
  "conceptual_understanding": 7,
  "practical_knowledge": 6,
  "clarity": 8,
  "confidence": 7,
  "final_score": 7.0,
  "feedback": "Good understanding of core concepts but could improve on practical examples.",
  "correct_answer": "A concise model answer covering the key points."
}}

Return ONLY the JSON object. No other text."""


# ──────────────────────────────────────────────
#  Gap Analysis
# ──────────────────────────────────────────────

GAP_ANALYSIS_PROMPT = """You are a career advisor. Analyze skill gaps for a candidate based on evaluation scores.

### Required Skills and Scores:
{skills_scores}

For each skill, provide a brief recommendation on how to improve.

Return ONLY valid JSON -- no explanation, no markdown:
{{
  "gaps": [
    {{
      "skill": "Docker",
      "score": 3.5,
      "priority": "HIGH",
      "is_required": true,
      "recommendation": "Focus on containerization fundamentals, practice with multi-stage builds."
    }}
  ]
}}

Priority rules:
- Score < 5 for a required skill → "HIGH"
- Score <= 7 for a required skill → "MEDIUM"
- Score > 7 or not required → "LOW"

Return ONLY the JSON object."""


# ──────────────────────────────────────────────
#  Learning Plan
# ──────────────────────────────────────────────

LEARNING_PLAN_PROMPT = """You are an expert learning path designer. Create a personalized learning roadmap for the following skill gaps.

### Skill Gaps:

{skill_gaps}

### Constraints:

* Available hours per day: {hours_per_day}
* Target weeks available: {target_weeks}

---

## INSTRUCTIONS

For each skill, create a structured list of topics with:

* Specific topics to study (MUST be ordered chronologically, starting with the most foundational prerequisite topics first)
* Recommended resources (courses, books, youtube playlists, documentation)
* Define milestones for each topic using practical tasks:

  * Mini-projects or progressively larger projects
  * Do NOT include deployment unless clearly required
* Adjacent/complementary skills to learn
* **Prerequisites**: Analyze logical dependencies between the provided skill gaps. If Skill B requires Skill A (e.g., Pandas requires Python), add the EXACT name of Skill A to the `prerequisites` list of Skill B. ONLY use exact skill names from the provided skill gaps list. If no prerequisite exists among the given skill gaps, leave it empty `[]`.

---

## IMPORTANT RULES

* Return ONLY raw JSON (no markdown, no extra text)
* **NO WEEK-BASED LOGIC**: Do NOT include "Week X" or any mention of weeks in topics, milestones, or descriptions.
* **Do NOT include a "week" field anywhere in your response** — it is not used and wastes tokens.
* Ensure JSON is complete and valid (no truncation, all brackets closed)
* Maintain full structure, do not omit any fields
* Be concise and avoid unnecessary detail
* If unsure, return safe defaults instead of incomplete output

---

## SEMANTIC + CLUSTERING RULE

* Skills may be grouped ONLY if strongly related
* If grouping happens:

  * Keep one main "skill"
  * Add ALL original skills inside "covers_skills"
* Do NOT lose any skill
* Every input skill must appear either:

  * as its own plan OR
  * inside "covers_skills"

---

## RESOURCE RULES

* Ensure all URLs are valid and usable
* Do NOT generate fake or broken links
* If exact resource is uncertain, provide a working search URL instead

Example:
https://www.coursera.org/search?query=sql%20for%20data%20science

* Keep maximum 2–3 resources per topic

---

## OUTPUT FORMAT

{{
"plans": [
{{
"skill": "Docker",
"covers_skills": [],
"priority": "HIGH",
"current_score": 3.5,
"target_score": 8.0,
"topics": [
{{
"topic": "Docker Fundamentals",
"difficulty_weight": 4,
"resources": [
{{
"title": "Docker Official Documentation",
"type": "documentation",
"url": "https://docs.docker.com"
}}
],
"milestones": [
"Build and run a container",
"Understand Dockerfile syntax"
]
}}
],
"adjacent_skills": ["Kubernetes", "CI/CD", "Linux"],
"prerequisites": ["Linux Fundamentals"]
}}
],
"summary": "A brief overall summary of the learning plan."
}}

---

## FINAL CONSTRAINT

* Do NOT make the response too long
* Prefer compact wording over detailed explanations
* Always complete JSON even if shortening content
"""