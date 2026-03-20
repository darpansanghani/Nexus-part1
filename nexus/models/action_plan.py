"""Data models for NEXUS action plans.

This module defines the structured output expected from the Gemini API
and allows type-safe manipulation of the data within the application.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any


@dataclass
class ImmediateAction:
    """Represents a single actionable step to be taken during an emergency."""
    id: str
    type: str
    title: str
    description: str
    agency: str
    priority: int
    estimated_time: str
    phone_number: Optional[str]
    verified: bool

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        if not isinstance(self.priority, int) or not (1 <= self.priority <= 10):
            raise ValueError(f"Priority must be an integer between 1 and 10, got {self.priority}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, omitting null fields."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class ActionPlan:
    """Represents the complete structured output from the AI engine."""
    intent: str
    severity: str
    confidence: float
    location: str
    affected_people: str
    immediate_actions: List[ImmediateAction]
    medical_summary: Optional[str]
    risk_factors: List[str]
    resources_needed: List[str]
    followup_actions: List[str]
    search_grounding: Optional[str]
    language_detected: str
    data_quality: str

    def __post_init__(self) -> None:
        """Validate fields and sort actions by priority."""
        valid_severities = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
        if self.severity not in valid_severities:
            raise ValueError(f"Invalid severity: {self.severity}")
        
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")

        # Ensure immediate_actions are proper dataclass instances, if passed as dicts
        for i, action in enumerate(self.immediate_actions):
            if isinstance(action, dict):
                self.immediate_actions[i] = ImmediateAction(**action)
                
        # Sort actions by priority ascending
        self.immediate_actions.sort(key=lambda a: a.priority)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the full ActionPlan to a dictionary, omitting null fields."""
        result = asdict(self)
        result["immediate_actions"] = [
            action.to_dict() if hasattr(action, 'to_dict') else 
            {k: v for k, v in action.items() if v is not None}
            for action in self.immediate_actions
        ]
        # Remove null root fields
        return {k: v for k, v in result.items() if v is not None}
