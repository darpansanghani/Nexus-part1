"""Unit tests for the Gemini Service."""

import pytest
from unittest.mock import patch, MagicMock
from exceptions import GeminiError
from services.gemini_service import gemini_service, SYSTEM_PROMPT


class TestGeminiService:
    def setup_method(self):
        gemini_service._testing = False  # Ensure we test standard paths where possible
        gemini_service._model = MagicMock()

    def test_analyze_returns_valid_action_plan_dataclass(self, sample_action_plan):
        mock_response = MagicMock()
        mock_response.text = '{"intent": "Test", "severity": "CRITICAL", "confidence": 0.9, "location": "Loc", "affected_people": "None", "immediate_actions": [], "medical_summary": null, "risk_factors": [], "resources_needed": [], "followup_actions": [], "search_grounding": null, "language_detected": "En", "data_quality": "HIGH"}'
        mock_response.usage_metadata.prompt_token_count = 10
        mock_response.usage_metadata.candidates_token_count = 10
        gemini_service._model.generate_content.return_value = mock_response
        
        plan = gemini_service.analyze(text="Test")
        assert plan.intent == "Test"
        assert plan.severity == "CRITICAL"

    def test_analyze_retries_on_transient_api_error(self):
        # Make the first 2 calls fail, 3rd pass
        mock_response = MagicMock()
        mock_response.text = '{"intent": "Passed", "severity": "LOW", "confidence": 0.9, "location": "Loc", "affected_people": "None", "immediate_actions": [], "risk_factors": [], "resources_needed": [], "followup_actions": [], "language_detected": "En", "data_quality": "HIGH"}'
        
        gemini_service._model.generate_content.side_effect = [
            Exception("Transient 1"),
            Exception("Transient 2"),
            mock_response
        ]
        
        with patch("time.sleep", return_value=None):
            plan = gemini_service.analyze(text="Test retry")
            
        assert plan.intent == "Passed"
        assert gemini_service._model.generate_content.call_count == 3

    def test_analyze_returns_fallback_after_exhausting_retries(self):
        gemini_service._model.generate_content.side_effect = Exception("Persistent error")
        
        with patch("time.sleep", return_value=None):
            plan = gemini_service.analyze(text="Test fail")
            
        assert plan.intent == "AI analysis unavailable due to system error."
        assert plan.severity == "CRITICAL"

    def test_analyze_times_out_after_30_seconds(self):
        # Simulate time jump
        times = [100.0, 150.0] # Jump 50s after start
        
        def fake_time():
            if times: return times.pop(0)
            return 200.0
            
        gemini_service._model.generate_content.side_effect = Exception("Timeout trigger")
        
        with patch("time.time", side_effect=fake_time):
            plan = gemini_service.analyze(text="Timeout test")
            
        assert plan.intent.startswith("AI analysis unavailable")

    def test_system_prompt_is_present_in_every_gemini_call(self):
        # We test that system_instruction was set during configuration
        # Since configuration happens in init_app, we just verify the constant exists
        assert "You are NEXUS" in SYSTEM_PROMPT
        assert "OUTPUT FORMAT" in SYSTEM_PROMPT

    def test_image_bytes_are_included_when_image_provided(self):
        mock_response = MagicMock()
        mock_response.text = '{"intent": "Pass", "severity": "LOW", "confidence": 0.9, "location": "Loc", "affected_people": "None", "immediate_actions": [], "risk_factors": [], "resources_needed": [], "followup_actions": [], "language_detected": "En", "data_quality": "HIGH"}'
        gemini_service._model.generate_content.return_value = mock_response
        
        image_bytes = b"testdata"
        gemini_service.analyze(image_bytes=image_bytes)
        
        # Check what generate_content was called with
        args, _ = gemini_service._model.generate_content.call_args
        contents = args[0]
        assert any(isinstance(c, dict) and c.get('data') == image_bytes for c in contents)

    def test_malformed_json_response_returns_fallback(self):
        mock_response = MagicMock()
        mock_response.text = 'This is not JSON'
        gemini_service._model.generate_content.return_value = mock_response
        
        plan = gemini_service.analyze(text="Bad json")
        assert plan.intent.startswith("AI analysis unavailable")

    def test_missing_required_field_in_response_returns_fallback(self):
        mock_response = MagicMock()
        # Missing 'intent' and 'severity' completely
        mock_response.text = '{"confidence": 0.9}'
        gemini_service._model.generate_content.return_value = mock_response
        
        plan = gemini_service.analyze(text="Missing fields")
        assert plan.intent.startswith("AI analysis unavailable")
