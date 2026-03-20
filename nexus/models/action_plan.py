"""Data models for NEXUS action plans.

This module defines the structured output expected from the Gemini API
and allows type-safe manipulation of the data within the application.
"""

from dataclasses import asdict, dataclass
from typing import Any

from exceptions import ValidationError


@dataclass
class ImmediateAction:
    """Represents a single actionable step to be taken during an emergency.
    
    Attributes:
        id: Unique identifier for the action.
        type: The type category of the action.
        title: Short title.
        description: Detailed explanation.
        agency: The responsible agency.
        priority: Priority level (1 indicates highest priority).
        estimated_time: Estimated time to complete.
        phone_number: Contact number if applicable.
        verified: Whether the action is ground-truth verified.
    """

    id: str
    type: str
    title: str
    description: str
    agency: str
    priority: int
    estimated_time: str
    phone_number: str | None
    verified: bool

    def __post_init__(self) -> None:
        """Validate fields after initialization.
        
        Raises:
            ValidationError: If priority is outside the 1-10 range.
        """
        if not isinstance(self.priority, int) or not (1 <= self.priority <= 10):
            raise ValidationError(f"Priority must be an integer between 1 and 10, got {self.priority}")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, omitting null fields.
        
        Returns:
            Dictionary representation of the instance without null values.
        """
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class ActionPlan:
    """Represents the complete structured output from the AI engine.
    
    Attributes:
        intent: The identified emergency intent.
        severity: Severity level (CRITICAL, HIGH, MEDIUM, LOW).
        confidence: AI confidence score (0.0 to 1.0).
        location: Extracted or inferred location.
        affected_people: Description of people affected.
        immediate_actions: Ordered list of immediate actions.
        medical_summary: Optional summary of medical issues.
        risk_factors: Identified risk factors.
        resources_needed: Needed resources.
        followup_actions: List of actions to take after immediate steps.
        search_grounding: Optional search grounding context.
        language_detected: The dominant language.
        data_quality: Assessment of input data quality.
    """

    intent: str
    severity: str
    confidence: float
    location: str
    affected_people: str
    immediate_actions: list[ImmediateAction]
    medical_summary: str | None
    risk_factors: list[str]
    resources_needed: list[str]
    followup_actions: list[str]
    search_grounding: str | None
    language_detected: str
    data_quality: str

    def __post_init__(self) -> None:
        """Validate fields and sort actions by priority.
        
        Raises:
            ValidationError: If severity or confidence values are invalid.
        """
        valid_severities = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
        if self.severity not in valid_severities:
            raise ValidationError(f"Invalid severity: {self.severity}")

        if not (0.0 <= self.confidence <= 1.0):
            raise ValidationError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")

        # Ensure immediate_actions are proper dataclass instances, if passed as dicts
        for i, action in enumerate(self.immediate_actions):
            if isinstance(action, dict):
                # Type checker ignores that dict is used to initialize dataclass
                self.immediate_actions[i] = ImmediateAction(**action)  # type: ignore[arg-type]

        # Sort actions by priority ascending
        self.immediate_actions.sort(key=lambda a: getattr(a, "priority", 10))

    def to_dict(self) -> dict[str, Any]:
        """Convert the full ActionPlan to a dictionary, omitting null fields.
        
        Returns:
            Dictionary representation without null values.
        """
        result = asdict(self)
        result["immediate_actions"] = [
            action.to_dict() if hasattr(action, "to_dict") else {k: v for k, v in action.items() if v is not None}  # type: ignore[attr-defined]
            for action in self.immediate_actions
        ]
        # Remove null root fields
        return {k: v for k, v in result.items() if v is not None}
