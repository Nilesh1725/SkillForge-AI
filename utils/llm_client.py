"""
Reusable async LLM client for Hugging Face Inference API via LangChain.

Features:
  - LangChain Integration via ChatHuggingFace
  - Configurable model, temperature, max tokens
  - Automatic retries with exponential backoff (via tenacity)
  - Timeout handling
  - Structured JSON output with validation
"""

from __future__ import annotations

import logging
import os
from typing import Any, Type, TypeVar

from dotenv import load_dotenv
import google.genai as genai
import google.genai.types as genai_types
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_core.messages import HumanMessage
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from utils.json_parser import parse_and_validate, parse_json_response

load_dotenv(override=True)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# ──────────────────────────────────────────────
#  Configuration
# ──────────────────────────────────────────────

HF_API_TOKEN: str = os.getenv("HF_API_TOKEN", "")
HF_MODEL_ID: str = os.getenv("HF_MODEL_ID", "meta-llama/Llama-3.1-8B")
HF_API_URL: str = os.getenv("HF_API_URL", "https://api-inference.huggingface.co/models")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL_ID: str = os.getenv("GEMINI_MODEL_ID", "gemini-3-flash-preview")
LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "120"))
LLM_MAX_RETRIES: int = int(os.getenv("LLM_MAX_RETRIES", "3"))
LLM_MAX_NEW_TOKENS: int = int(os.getenv("LLM_MAX_NEW_TOKENS", "8192"))  # High enough for large JSON
LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.3"))


class LLMError(Exception):
    """Raised when the LLM call fails after all retries."""


class LLMValidationError(LLMError):
    """Raised when the LLM output cannot be parsed/validated."""


# ──────────────────────────────────────────────
#  Internal: Inject global rules
# ──────────────────────────────────────────────

def _inject_rules(prompt: str) -> str:
    """Inject strict rules into prompt to stabilize LLM output."""
    rules = (
        "\n\nSTRICT OUTPUT RULES:"
        "\n- Return ONLY raw JSON. No markdown, no backticks, no extra text."
        "\n- Ensure JSON is ALWAYS complete. Never stop mid-output. Always close all brackets."
        "\n- Maintain full JSON structure. Do not omit any required keys."
        "\n- If unsure about any value, return a safe default instead of incomplete output."
        "\n- All numeric values must be valid numbers between 0 and 100."
        "\n- Be concise: use short, compact sentences. Avoid long explanations."
        "\n- Limit response size: prefer compressed wording to prevent truncation."
        "\n- Prioritize correctness over verbosity."
        "\n- Never generate partial JSON under any condition."
    )
    return prompt + rules


# ──────────────────────────────────────────────
#  Public API — raw text
# ──────────────────────────────────────────────

@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(LLM_MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
async def query_llm(
    prompt: str,
    model: str | None = None,
    max_new_tokens: int | None = None,
    temperature: float | None = None,
) -> str:
    """
    Query the LLM and return the raw generated text via LangChain ChatHuggingFace.

    Raises:
        LLMError: If all retry attempts fail.
    """
    hf_model = model or HF_MODEL_ID
    gemini_model_id = model or GEMINI_MODEL_ID
    max_new_tokens = max_new_tokens or LLM_MAX_NEW_TOKENS
    temperature = temperature if temperature is not None else LLM_TEMPERATURE

    # 🔥 Inject rules BEFORE first call
    prompt = _inject_rules(prompt)
    safe_temp = temperature if temperature > 0 else 0.001

    if GEMINI_API_KEY:
        try:
            logger.info("🚀 [LLM] Using Provider: Google Gemini | Model: %s", gemini_model_id)
            logger.info("🚀 [LLM] Prompt Content:\n%s", prompt)

            # Use native google-genai SDK with JSON mode and thinking budget
            client = genai.Client(api_key=GEMINI_API_KEY)
            
            # Gemini 3 Thinking configuration
            is_gemini_3 = "gemini-3" in gemini_model_id.lower()
            thinking_config = genai_types.ThinkingConfig(thinking_budget=1024) if is_gemini_3 else None
            
            gen_config = genai_types.GenerateContentConfig(
                temperature=safe_temp,
                max_output_tokens=LLM_MAX_NEW_TOKENS,
                response_mime_type="application/json",  # Forces clean JSON — no markdown fences
                thinking_config=thinking_config,
            )
            response = await client.aio.models.generate_content(
                model=gemini_model_id,
                contents=prompt,
                config=gen_config,
            )

            content = response.text
            if content and content.strip():
                logger.info("✅ [LLM] Google Gemini Raw Response:\n%s", content)
                return content.strip()
            else:
                logger.warning("⚠️ [LLM] Gemini returned empty response, falling back to Hugging Face...")
        except Exception as exc:
            logger.warning("⚠️ [LLM] Gemini API failed (%s). Falling back to Hugging Face API...", exc)

    logger.info("🚀 [LLM] Using Provider: Hugging Face | Model: %s", hf_model)
    logger.info("🚀 [LLM] Prompt Content:\n%s", prompt)

    try:
        endpoint = HuggingFaceEndpoint(
            repo_id=hf_model,
            huggingfacehub_api_token=HF_API_TOKEN,
            max_new_tokens=max_new_tokens,
            temperature=safe_temp,
            return_full_text=False,
            do_sample=safe_temp > 0,
            timeout=LLM_TIMEOUT,
        )

        chat_model = ChatHuggingFace(llm=endpoint)

        messages = [HumanMessage(content=prompt)]
        response = await chat_model.ainvoke(messages)

        if not response.content:
            raise LLMError("LLM returned empty response")

        logger.info("✅ [LLM] Hugging Face Raw Response:\n%s", response.content)
        return str(response.content)

    except Exception as exc:
        logger.error("LangChain ChatHuggingFace API error: %s", exc)
        raise LLMError(f"LangChain ChatHuggingFace API error: {exc}") from exc


# ──────────────────────────────────────────────
#  Public API — parsed JSON
# ──────────────────────────────────────────────

async def query_llm_json(
    prompt: str,
    model: str | None = None,
    max_new_tokens: int | None = None,
    temperature: float | None = None,
) -> dict[str, Any] | list[Any]:
    """
    Query the LLM and parse the response as JSON.
    Retries up to 2 extra times if JSON parsing fails.
    """
    last_error: Exception | None = None

    for attempt in range(3):
        raw = await query_llm(prompt, model, max_new_tokens, temperature)
        try:
            parsed_data = parse_json_response(raw)
            logger.info("✅ [LLM] JSON Parsed Successfully: %s", parsed_data)
            return parsed_data
        except ValueError as exc:
            last_error = exc
            logger.warning("⚠️ [LLM] JSON parse attempt %d failed: %s", attempt + 1, exc)

            if attempt < 2:
                prompt = prompt + (
                    "\n\nIMPORTANT:"
                    "\n- Return ONLY valid JSON"
                    "\n- No explanation"
                    "\n- match_percentage must be between 0 and 100"
                )

    raise LLMValidationError(f"Failed to get valid JSON after 3 attempts: {last_error}")


# ──────────────────────────────────────────────
#  Public API — validated Pydantic model
# ──────────────────────────────────────────────

async def query_llm_structured(
    prompt: str,
    response_model: Type[T],
    model: str | None = None,
    max_new_tokens: int | None = None,
    temperature: float | None = None,
) -> T:
    """
    Query the LLM, parse JSON, and validate against a Pydantic model.
    Retries up to 2 extra times if validation fails.
    """
    last_error: Exception | None = None

    for attempt in range(3):
        raw = await query_llm(prompt, model, max_new_tokens, temperature)
        try:
            parsed_data = parse_and_validate(raw, response_model)
            logger.info("✅ [LLM] Structured Data Validated Successfully (%s)", response_model.__name__)
            return parsed_data

        except (ValueError, Exception) as exc:
            last_error = exc
            logger.warning(
                "⚠️ [LLM] Structured parse attempt %d failed for %s: %s",
                attempt + 1,
                response_model.__name__,
                exc,
            )

            if attempt < 2:
                prompt = prompt + (
                    "\n\nIMPORTANT RULES:"
                    "\n- Return ONLY valid JSON"
                    "\n- Do NOT include explanations or markdown"
                    "\n- match_percentage must be between 0 and 100"
                    "\n- Do NOT exceed 100"
                )

    raise LLMValidationError(
        f"Failed to get valid {response_model.__name__} after 3 attempts: {last_error}"
    )