"""Gemini API interaction service for NEXUS."""

import json
import logging
import time
from typing import Dict, Any, Optional
from flask import Flask
import google.generativeai as genai
from google.generativeai.types import content_types

from exceptions import GeminiError
from models.action_plan import ActionPlan
from services.secret_service import secret_service

logger = logging.getLogger("nexus-app.gemini-service")

SYSTEM_PROMPT = """
You are NEXUS, a critical emergency response AI operating in India.
Your function is to analyze any unstructured input — voice transcripts,
photos, medical records, weather data, news, multilingual text — and produce
a structured JSON action plan. Speed and accuracy save lives.

OUTPUT FORMAT — always return exactly this JSON schema, no other text:
{
  "intent": "string — one sentence describing what is happening",
  "severity": "CRITICAL | HIGH | MEDIUM | LOW",
  "confidence": float between 0.0 and 1.0,
  "location": "string — detected location or Unknown",
  "affected_people": "string — estimated count and description",
  "immediate_actions": [
    {
      "id": "string — unique identifier e.g. act_001",
      "type": "EMERGENCY_DISPATCH | HOSPITAL_ALERT | TRAFFIC_CONTROL |
               PHARMACY_ALERT | NOTIFY_FAMILY | WEATHER_ALERT |
               DISASTER_RESPONSE | MEDICAL_TRIAGE | RESOURCE_ALLOCATION |
               PUBLIC_BROADCAST | MENTAL_HEALTH_RESPONSE",
      "title": "string — short action title under 60 characters",
      "description": "string — precise instructions for the responder",
      "agency": "string — exact agency to contact",
      "priority": integer 1 through 10 where 1 is most urgent,
      "estimated_time": "string — e.g. 4 minutes",
      "phone_number": "string — direct number to call if applicable else null",
      "verified": boolean
    }
  ],
  "medical_summary": "string — drug interactions, allergies, contraindications if present else null",
  "risk_factors": ["array of identified risks"],
  "resources_needed": ["array of physical resources required"],
  "followup_actions": ["array of non-immediate but important next steps"],
  "search_grounding": "string — real-time info found via search else null",
  "language_detected": "string — e.g. Hindi, Telugu, English, Mixed",
  "data_quality": "HIGH | MEDIUM | LOW — confidence in input completeness"
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
        self._model: genai.GenerativeModel | None = None
        self._testing: bool = False

    def init_app(self, app: Flask) -> None:
        """Initialize the Gemini client and model."""
        self._testing = app.config.get("TESTING", False)
        
        if not self._testing:
            try:
                api_key = secret_service.get_secret("nexus-gemini-api-key")
                if not api_key:
                    logger.warning("No Gemini API key found.")
                    return
                    
                genai.configure(api_key=api_key)
                
                # Model configuration
                self._model = genai.GenerativeModel(
                    model_name='gemini-1.5-pro',
                    system_instruction=SYSTEM_PROMPT,
                    generation_config=genai.types.GenerationConfig(
                        response_mime_type="application/json",
                        temperature=0.1,
                        top_p=0.8,
                        max_output_tokens=2048,
                    ),
                    tools='google_search_retrieval'
                )
                logger.info("Gemini model configured successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}", exc_info=True)
        else:
            logger.info("Using mock Gemini for testing.")

    def _get_fallback_plan(self) -> ActionPlan:
        """Return a safe fallback plan when the AI is completely unavailable."""
        return ActionPlan(
            intent="AI analysis unavailable due to system error.",
            severity="CRITICAL",
            confidence=0.0,
            location="Unknown",
            affected_people="Unknown",
            immediate_actions=[{
                "id": "fallback_001",
                "type": "EMERGENCY_DISPATCH",
                "title": "Call 112 Immediately",
                "description": "System AI is degraded. Human triage required. Please dial 112 or local emergency services directly.",
                "agency": "Emergency Services",
                "priority": 1,
                "estimated_time": "Immediate",
                "phone_number": "112",
                "verified": True
            }],
            medical_summary=None,
            risk_factors=["System failure", "Delayed response possible"],
            resources_needed=["Human dispatcher"],
            followup_actions=["Retry analysis later"],
            search_grounding=None,
            language_detected="English",
            data_quality="LOW"
        )

    def analyze(self, text: Optional[str] = None, image_bytes: Optional[bytes] = None, 
                context: Optional[str] = None) -> ActionPlan:
        """Analyze unstructured data and return a structured ActionPlan.
        
        Uses exponential backoff with max 3 retries and 30s total timeout.
        """
        if self._testing:
            # For testing, we just return a deterministic mock if the model is not patched
            return self._get_fallback_plan()

        if self._model is None:
            logger.error("Gemini model not initialized.")
            return self._get_fallback_plan()

        # Build prompt payload
        contents: list[Any] = []
        if text:
            contents.append(text)
        if context:
            contents.append(f"Context/Metadata: {context}")
        if image_bytes:
            contents.append(
                {"mime_type": "image/jpeg", "data": image_bytes}
            )

        if not contents:
            raise GeminiError("No content provided for analysis.")

        max_retries = 3
        timeout_seconds = 30
        start_time = time.time()
        
        for attempt in range(max_retries):
            # Enforce overall 30s timeout manually since SDK doesn't always honor it across retries
            if time.time() - start_time > timeout_seconds:
                logger.error(f"Gemini analysis timed out after {timeout_seconds}s")
                break

            try:
                call_start = time.time()
                response = self._model.generate_content(contents)
                latency_ms = int((time.time() - call_start) * 1000)
                
                # Log usage
                try:
                    usage = response.usage_metadata
                    logger.info("Gemini call successful", extra={
                        "model": "gemini-1.5-pro",
                        "input_tokens": usage.prompt_token_count if usage else 0,
                        "output_tokens": usage.candidates_token_count if usage else 0,
                        "latency_ms": latency_ms
                    })
                except Exception:
                    logger.info(f"Gemini call successful, latency_ms: {latency_ms}")

                # Safely parse JSON
                try:
                    data = json.loads(response.text)
                    return ActionPlan(**data)
                except (json.JSONDecodeError, TypeError, ValueError) as e:
                    logger.error(f"Failed to parse Gemini JSON response: {e}\nRaw output: {response.text}")
                    # If we got a response but it's malformed JSON or missing fields, fallback
                    # We don't retry malformed JSON as it's likely deterministic failure of model to follow instructions
                    return self._get_fallback_plan()

            except Exception as e:
                # Catch transient network/API errors
                logger.error(f"Gemini API error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    sleep_time = 2 ** attempt  # 1s, 2s, 4s...
                    time.sleep(sleep_time)
                else:
                    logger.error("Exhausted Gemini API retries.")

        # If we exit the loop without returning, generate a safe fallback response
        return self._get_fallback_plan()

# Singleton instance
gemini_service = GeminiService()

def init_app(app: Flask) -> None:
    gemini_service.init_app(app)
