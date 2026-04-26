"""
AI Interview Agent — FastAPI Application Entry Point

Production-ready backend for AI-powered interview system:
  - Skill extraction & matching (JD vs Resume)
  - Adaptive interview question generation
  - Answer evaluation with structured scoring
  - Gap analysis with priority categorization
  - Personalized learning plan generation

Powered by Hugging Face Inference API (LLaMA / Mixtral models).
"""

from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

# ──────────────────────────────────────────────
#  Bootstrap
# ──────────────────────────────────────────────

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if os.getenv("DEBUG", "false").lower() == "true" else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
#  Lifespan (startup / shutdown)
# ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle manager."""
    # ── Startup ──
    hf_token = os.getenv("HF_API_TOKEN", "")
    model_id = os.getenv("HF_MODEL_ID", "meta-llama/Meta-Llama-3-8B-Instruct")

    if not hf_token or hf_token == "hf_your_token_here":
        logger.warning(
            "HF_API_TOKEN not set! Set it in .env or environment variables. "
            "The API will return 502 errors for LLM calls."
        )
    else:
        logger.info("HF API token configured (model: %s)", model_id)

    logger.info("AI Interview Agent started successfully")

    yield

    # ── Shutdown ──
    logger.info("AI Interview Agent shutting down")


# ──────────────────────────────────────────────
#  App Factory
# ──────────────────────────────────────────────

app = FastAPI(
    title="AI Interview Agent",
    description=(
        "AI-powered interview system that extracts skills from resumes and job descriptions, "
        "conducts adaptive interviews, evaluates answers with structured scoring, "
        "performs gap analysis, and generates personalized learning plans. "
        "Powered by Hugging Face LLaMA models."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global Exception Handler ──
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected error occurred. Please try again later.",
            "error_type": type(exc).__name__,
        },
    )


# ──────────────────────────────────────────────
#  Routes
# ──────────────────────────────────────────────

from routes.analyze import router as analyze_router
from routes.interview import router as interview_router
from routes.evaluation import router as evaluation_router
from routes.learning import router as learning_router

app.include_router(analyze_router)
app.include_router(interview_router)
app.include_router(evaluation_router)
app.include_router(learning_router)

# ── Frontend ──
import os
frontend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
app.mount("/app", StaticFiles(directory=frontend_path, html=True), name="frontend")


@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to frontend."""
    return RedirectResponse(url="/app/")


@app.get("/health", tags=["Health"])
async def health():
    """Detailed health check."""
    hf_token = os.getenv("HF_API_TOKEN", "")
    return {
        "status": "healthy",
        "llm_configured": bool(hf_token and hf_token != "hf_your_token_here"),
        "model": os.getenv("HF_MODEL_ID", "meta-llama/Meta-Llama-3-8B-Instruct"),
    }


# ──────────────────────────────────────────────
#  Entry Point
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("DEBUG", "false").lower() == "true",
        log_level="debug" if os.getenv("DEBUG", "false").lower() == "true" else "info",
    )
