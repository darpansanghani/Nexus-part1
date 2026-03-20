"""Gemini API interaction service for NEXUS."""

import json
import os
import time
from typing import Any

from flask import Flask
import google.generativeai as genai

from constants import (
    GEMINI_API_TIMEOUT_SECONDS,
    GEMINI_MAX_RETRIES,
    GEMINI_RETRY_BACKOFF,
    GEMINI_RETRY_DELAY_SECONDS,
)
from exceptions import GeminiError
from logger import get_logger
from models.action_plan import ActionPlan
from services.secret_service import secret_service

logger = get_logger(__name__)

SYSTEM_PROMPT = """
You are NEXUS, a critical emergency response AI operating in India.
Your function is to analyze any unstructured input — voice transcripts,
photos, medical records, weather data, news, multilingual text — and produce
a structured JSON action plan. Speed and accuracy save lives.

OUTPUT FORMAT — always return exactly this JSON schema, no other text:
{
  "intent": "string — one sentence describing what is happening",
  "severity": "CRITICAL",
  "confidence": 0.9,
  "location": "string — detected location or Unknown",
  "affected_people": "string — estimated count and description",
  "immediate_actions": [
    {
      "id": "string — unique identifier e.g. act_001",
      "type": "EMERGENCY_DISPATCH",
      "title": "string — short action title under 60 characters",
      "description": "string — precise instructions for the responder",
      "agency": "string — exact agency to contact",
      "priority": 1,
      "estimated_time": "string — e.g. 4 minutes",
      "phone_number": "string — direct number to call if applicable else null",
      "verified": true
    }
  ],
  "medical_summary": "string — drug interactions, allergies, contraindications if present else null",
  "risk_factors": ["array of identified risks"],
  "resources_needed": ["array of physical resources required"],
  "followup_actions": ["array of non-immediate but important next steps"],
  "search_grounding": "string — real-time info found via search else null",
  "language_detected": "string — e.g. Hindi, Telugu, English, Mixed",
  "data_quality": "HIGH"
}

Critical rules you must always follow:
1. Sort immediate_actions by priority ascending — priority 1 first
2. For any medical input: ALWAYS check drug interactions and flag them clearly
3. India emergency numbers: 108 ambulance, 100 police, 101 fire, 1091 women helpline
4. If severity is CRITICAL: generate a minimum of 3 immediate_actions
5. If input mentions a child or elderly person: escalate severity by one level
6. If fuel leak or chemical smell is mentioned: always add a fire brigade action
7. If confidence is below 0.6: add a clarification request in followup_actions
8. Never invent phone numbers — only use numbers verified via search or well known
"""


class GeminiService:
    """Manages AI analysis via Gemini 1.5 Pro."""

    def __init__(self) -> None:
        """Initialize the GeminiService."""
        self._model: genai.GenerativeModel | None = None
        self._testing: bool = False

    def init_app(self, app: Flask) -> None:
        """Initialize the Gemini client and model.

        Args:
            app: The Flask application instance.
        """
        self._testing = app.config.get("TESTING", False)

        if not self._testing:
            try:
                # Tier 1: Try Secret Manager (or env var via secret_service)
                api_key = secret_service.get_secret("nexus-gemini-api-key")
                logger.info("Secret service returned key", extra={"has_key": bool(api_key)})

                # Tier 2: Direct env var fallback (catches any Secret Manager failures)
                if not api_key:
                    api_key = os.environ.get("GEMINI_API_KEY", "")
                    if api_key:
                        logger.info("Gemini API key resolved from GEMINI_API_KEY env var directly.")
                    else:
                        logger.error(
                            "Gemini API key not found in Secret Manager OR GEMINI_API_KEY env var. "
                            "Set GEMINI_API_KEY in Cloud Run environment variables or create the "
                            "'nexus-gemini-api-key' secret in Secret Manager."
                        )
                        return

                genai.configure(api_key=api_key)

                # Model configuration
                self._model = genai.GenerativeModel(
                    model_name="gemini-1.5-pro",
                    system_instruction=SYSTEM_PROMPT,
                    generation_config=genai.types.GenerationConfig(
                        response_mime_type="application/json",
                        temperature=0.1,
                        top_p=0.8,
                        max_output_tokens=2048,
                    ),
                    tools="google_search_retrieval",
                )
                logger.info("Gemini model configured successfully.")
            except Exception:
                logger.exception("Failed to initialize Gemini")
        else:
            logger.info("Using mock Gemini for testing.")


    def _get_fallback_plan(self) -> ActionPlan:
        """Return a safe fallback plan when the AI is completely unavailable.

        Returns:
            A pre-configured ActionPlan for system errors.
        """
        return ActionPlan(
            intent="AI analysis unavailable due to system error.",
            severity="CRITICAL",
            confidence=0.0,
            location="Unknown",
            affected_people="Unknown",
            immediate_actions=[
                {
                    "id": "fallback_001",
                    "type": "EMERGENCY_DISPATCH",
                    "title": "Call 112 Immediately",
                    "description": "System AI is degraded. Human triage required. Please dial 112 directly.",
                    "agency": "Emergency Services",
                    "priority": 1,
                    "estimated_time": "Immediate",
                    "phone_number": "112",
                    "verified": True,
                }
            ], # type: ignore[arg-type]
            medical_summary=None,
            risk_factors=["System failure", "Delayed response possible"],
            resources_needed=["Human dispatcher"],
            followup_actions=["Retry analysis later"],
            search_grounding=None,
            language_detected="English",
            data_quality="LOW",
        )

    def analyze(
        self, text: str | None = None, image_bytes: bytes | None = None, context: str | None = None
    ) -> ActionPlan:
        """Analyze unstructured data and return a structured ActionPlan.

        Uses exponential backoff with retries and a global timeout.

        Args:
            text: Optional text input.
            image_bytes: Optional image data in bytes.
            context: Optional contextual metadata string.

        Returns:
            A validated ActionPlan object.

        Raises:
            GeminiError: If no content is provided.
        """
        if self._model is None:
            if not self._testing:
                logger.error("Gemini model not initialized.")
            return self._get_fallback_plan()

        # Build prompt payload
        contents: list[Any] = []
        if text:
            contents.append(text)
        if context:
            contents.append(f"Context/Metadata: {context}")
        if image_bytes:
            contents.append({"mime_type": "image/jpeg", "data": image_bytes})

        if not contents:
            raise GeminiError("No content provided for analysis.")

        start_time = time.time()

        for attempt in range(GEMINI_MAX_RETRIES):
            # Enforce overall timeout manually since SDK doesn't always honor it across retries
            if time.time() - start_time > GEMINI_API_TIMEOUT_SECONDS:
                logger.error("Gemini analysis timed out", extra={"timeout": GEMINI_API_TIMEOUT_SECONDS})
                break

            try:
                call_start = time.time()
                response = self._model.generate_content(contents)
                latency_ms = int((time.time() - call_start) * 1000)

                # Log usage
                try:
                    usage = response.usage_metadata
                    logger.info(
                        "Gemini call successful",
                        extra={
                            "model": "gemini-1.5-pro",
                            "input_tokens": getattr(usage, "prompt_token_count", 0),
                            "output_tokens": getattr(usage, "candidates_token_count", 0),
                            "latency_ms": latency_ms,
                        },
                    )
                except Exception:
                    logger.info("Gemini call successful", extra={"latency_ms": latency_ms})

                # Safely parse JSON
                try:
                    data = json.loads(response.text)
                    return ActionPlan(**data)
                except (json.JSONDecodeError, TypeError, ValueError) as e:
                    logger.error(f"Failed to parse Gemini JSON response: {e}\nRaw output: {response.text}")
                    return self._get_fallback_plan()

            except Exception as e:
                # Catch transient network/API errors
                logger.warning(
                    "Gemini API error", extra={"attempt": attempt + 1, "max_retries": GEMINI_MAX_RETRIES, "error": str(e)}
                )
                if attempt < GEMINI_MAX_RETRIES - 1:
                    sleep_time = GEMINI_RETRY_DELAY_SECONDS * (GEMINI_RETRY_BACKOFF ** attempt)
                    time.sleep(sleep_time)
                else:
                    logger.error("Exhausted Gemini API retries.", exc_info=True)

        return self._get_fallback_plan()


# Singleton instance
gemini_service = GeminiService()


def init_app(app: Flask) -> None:
    """Initialize the global Gemini service.

    Args:
        app: The Flask app instance.
    """
    gemini_service.init_app(app)
