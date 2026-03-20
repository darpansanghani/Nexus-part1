"""Tests for data models."""

import pytest

from exceptions import ValidationError
from models.action_plan import ActionPlan, ImmediateAction


class TestModels:
    """Tests for ActionPlan and ImmediateAction models."""

    def test_action_plan_constructs_with_valid_data(self) -> None:
        """Data instantiation."""
        plan = ActionPlan(
            intent="Test",
            severity="CRITICAL",
            confidence=1.0,
            location="Test",
            affected_people="0",
            immediate_actions=[],
            medical_summary=None,
            risk_factors=[],
            resources_needed=[],
            followup_actions=[],
            search_grounding=None,
            language_detected="En",
            data_quality="HIGH",
        )
        assert plan.intent == "Test"
        assert plan.severity == "CRITICAL"

    def test_action_plan_rejects_invalid_severity(self) -> None:
        """Constraint invalid severity."""
        with pytest.raises(ValidationError):
            ActionPlan(
                intent="T",
                severity="INVALID",
                confidence=0.5,
                location="v",
                affected_people="1",
                immediate_actions=[],
                medical_summary=None,
                risk_factors=[],
                resources_needed=[],
                followup_actions=[],
                search_grounding=None,
                language_detected="en",
                data_quality="HIGH",
            )

    def test_action_plan_rejects_confidence_above_1(self) -> None:
        """Constraint max conf."""
        with pytest.raises(ValidationError):
            ActionPlan(
                intent="T",
                severity="HIGH",
                confidence=1.5,
                location="v",
                affected_people="1",
                immediate_actions=[],
                medical_summary=None,
                risk_factors=[],
                resources_needed=[],
                followup_actions=[],
                search_grounding=None,
                language_detected="en",
                data_quality="HIGH",
            )

    def test_action_plan_rejects_confidence_below_0(self) -> None:
        """Constraint min conf."""
        with pytest.raises(ValidationError):
            ActionPlan(
                intent="T",
                severity="HIGH",
                confidence=-0.5,
                location="v",
                affected_people="1",
                immediate_actions=[],
                medical_summary=None,
                risk_factors=[],
                resources_needed=[],
                followup_actions=[],
                search_grounding=None,
                language_detected="en",
                data_quality="HIGH",
            )

    def test_immediate_action_rejects_priority_above_10(self) -> None:
        """Constraint immediate action max priority."""
        with pytest.raises(ValidationError):
            ImmediateAction(
                id="1",
                type="DISPATCH",
                title="T",
                description="D",
                agency="A",
                priority=11,
                estimated_time="1m",
                phone_number=None,
                verified=False,
            )

    def test_action_plan_to_dict_excludes_null_fields(self) -> None:
        """Ensure serialization removes null values."""
        plan = ActionPlan(
            intent="Test",
            severity="LOW",
            confidence=0.5,
            location="Test",
            affected_people="0",
            immediate_actions=[],
            medical_summary=None,
            risk_factors=[],
            resources_needed=[],
            followup_actions=[],
            search_grounding=None,
            language_detected="En",
            data_quality="HIGH",
        )
        d = plan.to_dict()
        assert "medical_summary" not in d
        assert "search_grounding" not in d

    def test_actions_sorted_by_priority_on_construction(self) -> None:
        """Ensure actions are automatically sorted."""
        a1 = ImmediateAction("1", "T", "T", "D", "A", 3, "1m", None, True)
        a2 = ImmediateAction("2", "T", "T", "D", "A", 1, "1m", None, True)

        plan = ActionPlan(
            intent="Test",
            severity="LOW",
            confidence=0.5,
            location="Test",
            affected_people="0",
            immediate_actions=[a1, a2],
            medical_summary=None,
            risk_factors=[],
            resources_needed=[],
            followup_actions=[],
            search_grounding=None,
            language_detected="En",
            data_quality="HIGH",
        )
        assert plan.immediate_actions[0].id == "2"
        assert plan.immediate_actions[1].id == "1"
