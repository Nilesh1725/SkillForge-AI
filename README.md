# 🤖 AI Interview Agent

A production-ready FastAPI backend for an AI-powered interview and skill assessment system. Supports **Google Gemini** (primary) and **Hugging Face LLaMA** (fallback) — no OpenAI dependency.

## 🎯 What It Does

| Feature | Description |
|---------|-------------|
| **Skill Extraction** | Extracts skills from Job Description + Resume using LLM |
| **Skill Matching** | Deterministic 5-layer matching: exact → synonym → sub-skill hierarchy → inferred → contextual |
| **Adaptive Interview** | Generates difficulty-adjusted questions (easy/medium/hard) |
| **Answer Evaluation** | Structured scoring across 4 dimensions with model answers |
| **Gap Analysis** | Priority-based skill gap categorization (HIGH/MEDIUM/LOW) |
| **Learning Plans** | Week-by-week personalized roadmaps with resources |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI App                             │
├─────────────────────────────────────────────────────────────────┤
│  Routes                                                         │
│  ├── POST /analyze           → Skill extraction + matching      │
│  ├── POST /generate-questions → Adaptive question gen           │
│  ├── POST /evaluate          → Answer scoring                   │
│  ├── POST /gap-analysis      → Skill gap categorization         │
│  └── POST /learning-plan     → Learning roadmap                 │
├─────────────────────────────────────────────────────────────────┤
│  Services                                                       │
│  ├── skill_extractor.py      → LLM-based extraction             │
│  ├── skill_matcher.py        → Deterministic 5-layer matching   │
│  ├── skill_mappings.py       → Synonym, hierarchy & semantic    │
│  ├── proficiency_engine.py   → Evidence-based proficiency       │
│  ├── question_generator.py   → Difficulty-adaptive questions    │
│  ├── evaluator.py            → Structured scoring               │
│  ├── gap_analysis.py         → Priority categorization          │
│  └── learning_plan.py        → Roadmap generation               │
├─────────────────────────────────────────────────────────────────┤
│  Utils                                                          │
│  ├── llm_client.py           → Gemini / HF API client           │
│  ├── json_parser.py          → Robust JSON extraction           │
│  ├── prompts.py              → Centralized prompt templates     │
│  └── validators.py           → Validation helpers               │
├─────────────────────────────────────────────────────────────────┤
│  Models                                                         │
│  └── schemas.py              → Pydantic request/response        │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────┐     ┌──────────────────────┐
│  Google Gemini API  │     │  Hugging Face API     │
│  (primary)          │     │  (fallback)           │
└─────────────────────┘     └──────────────────────┘
```

> 📖 See [logic.md](logic.md) for a detailed breakdown of data flow and matching logic.

## ⚡ Quick Start

### 1. Clone & Install

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Hugging Face API

1. Go to [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
2. Create a new token with **Read** access
3. For gated models (like LLaMA 3), accept the model's license agreement on its model page
4. Create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env`:

```env
HF_API_TOKEN=hf_your_actual_token_here
HF_MODEL_ID=meta-llama/Meta-Llama-3-8B-Instruct
```

**Recommended models:**
- `meta-llama/Meta-Llama-3-8B-Instruct` — Best balance of quality and speed
- `mistralai/Mixtral-8x7B-Instruct-v0.1` — Strong alternative
- `meta-llama/Meta-Llama-3-70B-Instruct` — Highest quality (slower)

### 3. Run the Server

```bash
# Development mode (with hot reload)
python main.py

# Or directly with uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Open API Docs

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

## 🔌 API Endpoints

### `POST /analyze` — Skill Extraction & Matching

```json
{
  "job_description": "We need a Python developer with FastAPI, Docker, and PostgreSQL experience...",
  "resume": "Experienced software engineer with 5 years in Python, Flask, Docker..."
}
```

**Response:**
```json
{
  "jd_skills": ["Python", "FastAPI", "Docker", "PostgreSQL"],
  "resume_skills": ["Python", "Flask", "Docker", "MySQL"],
  "matched_skills": [
    {"skill": "Python", "found_in_resume": true, "proficiency_estimate": "advanced"},
    {"skill": "Docker", "found_in_resume": true, "proficiency_estimate": "intermediate"},
    {"skill": "FastAPI", "found_in_resume": false, "proficiency_estimate": "unknown"},
    {"skill": "PostgreSQL", "found_in_resume": false, "proficiency_estimate": "unknown"}
  ],
  "match_percentage": 50.0,
  "missing_skills": ["FastAPI", "PostgreSQL"]
}
```

### `POST /generate-questions` — Interview Questions

```json
{
  "skill": "Python",
  "difficulty": "medium",
  "count": 3,
  "context": "Backend development role"
}
```

### `POST /evaluate` — Answer Evaluation

```json
{
  "question": "Explain Python's GIL and its impact on multithreading.",
  "answer": "The GIL is a mutex that protects access to Python objects...",
  "skill": "Python",
  "difficulty": "medium"
}
```

**Response:**
```json
{
  "skill": "Python",
  "difficulty": "medium",
  "evaluation": {
    "conceptual_understanding": 8,
    "practical_knowledge": 7,
    "clarity": 9,
    "confidence": 7,
    "final_score": 7.7,
    "feedback": "Strong conceptual grasp of GIL. Consider adding examples of when to use multiprocessing vs threading.",
    "correct_answer": "The GIL (Global Interpreter Lock) is..."
  },
  "next_difficulty": "hard"
}
```

### `POST /gap-analysis` — Skill Gap Analysis

```json
{
  "required_skills": ["Python", "FastAPI", "Docker", "PostgreSQL"],
  "scores": {
    "Python": 8.5,
    "FastAPI": 3.0,
    "Docker": 6.0,
    "PostgreSQL": 4.5
  }
}
```

### `POST /learning-plan` — Learning Roadmap

```json
{
  "skill_gaps": [
    {"skill": "FastAPI", "score": 3.0, "priority": "HIGH", "is_required": true, "recommendation": "Focus on FastAPI fundamentals"},
    {"skill": "PostgreSQL", "score": 4.5, "priority": "HIGH", "is_required": true, "recommendation": "Learn SQL and database design"}
  ],
  "available_hours_per_day": 2.0,
  "target_weeks": 8
}
```

## 🧠 Adaptive Interview Logic

The system adjusts question difficulty based on evaluation scores:

```
Score > 7  →  Next question: HARD
Score < 4  →  Next question: EASY
Otherwise  →  Next question: MEDIUM
```

## 🔐 LLM Output Safety

LLaMA models may not always produce valid JSON. This system uses a **4-layer defense**:

1. **Prompt Engineering** — Every prompt includes strict JSON instructions + examples
2. **JSON Extraction** — Regex-based extraction from markdown fences, prose wrappers
3. **Auto-Fix** — Trailing commas, quote normalization, control character removal
4. **Pydantic Validation** — Schema enforcement with retry (up to 3 attempts)

## 📁 Project Structure

```
project/
├── main.py                      # FastAPI app entry point
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variable template
├── README.md                    # This file
├── logic.md                     # Data flow & matching logic docs
├── models/
│   └── schemas.py               # Pydantic request/response schemas
├── routes/
│   ├── analyze.py               # POST /analyze
│   ├── interview.py             # POST /generate-questions
│   ├── evaluation.py            # POST /evaluate, /gap-analysis
│   └── learning.py              # POST /learning-plan
├── services/
│   ├── skill_extractor.py       # LLM skill extraction
│   ├── skill_matcher.py         # Deterministic 5-layer matching
│   ├── skill_mappings.py        # Synonym, hierarchy & semantic maps
│   ├── proficiency_engine.py    # Evidence-based proficiency scoring
│   ├── question_generator.py    # Interview question generation
│   ├── evaluator.py             # Answer evaluation & scoring
│   ├── gap_analysis.py          # Skill gap categorization
│   └── learning_plan.py         # Learning roadmap generation
├── frontend/
│   ├── index.html               # Main UI page
│   ├── script.js                # Frontend logic
│   └── styles.css               # Styles
└── utils/
    ├── llm_client.py            # Gemini / HF Inference API client
    ├── json_parser.py           # Robust JSON extraction
    ├── prompts.py               # Centralized prompt templates
    └── validators.py            # Validation helpers
```

## 🛠️ Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | — | Google Gemini API key (primary provider) |
| `GEMINI_MODEL_ID` | `gemini-3-flash-preview` | Gemini model ID |
| `HF_API_TOKEN` | — | Hugging Face API token (fallback provider) |
| `HF_MODEL_ID` | `meta-llama/Meta-Llama-3-8B-Instruct` | HF model ID |
| `HF_API_URL` | `https://api-inference.huggingface.co/models` | HF API base URL |
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8000` | Server port |
| `DEBUG` | `true` | Enable debug mode + hot reload |
| `LLM_TIMEOUT` | `120` | API call timeout (seconds) |
| `LLM_MAX_RETRIES` | `3` | Max HTTP retry attempts |
| `LLM_MAX_NEW_TOKENS` | `8192` | Max tokens in LLM response |
| `LLM_TEMPERATURE` | `0.3` | LLM temperature (lower = more deterministic) |

## 📝 Documentation
- [Logic & Data Flow](logic.md) — Detailed breakdown of matching algorithms.
- [Deployment Guide](DEPLOYMENT.md) — Steps for Render, Docker, and production.
- [Contributing](CONTRIBUTING.md) — How to add skills and run tests.
- [Sample Input/Output](sample_input_output.md) — Examples of API requests and responses.
- [Changelog](CHANGELOG.md) — Project history.

## 📝 License
MIT
