"""pytest fixtures for NEXUS."""

from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app
from models.action_plan import ActionPlan, ImmediateAction


@pytest.fixture
def app() -> Generator[Flask, None, None]:
    """Create a testing app instance.

    Yields:
        Configured Flask app.
    """
    app_instance = create_app("testing")
    with app_instance.app_context():
        # Setup mock configurations internally
        pass
    yield app_instance


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Test client for the app.

    Args:
        app: The current active test Flask app.

    Returns:
        Test client.
    """
    return app.test_client()


@pytest.fixture
def sample_action_plan() -> ActionPlan:
    """A valid fully-populated ActionPlan dataclass instance.

    Returns:
        A populated mock ActionPlan.
    """
    return ActionPlan(
        intent="Test Intent",
        severity="CRITICAL",
        confidence=0.95,
        location="123 Test St",
        affected_people="5 injured",
        immediate_actions=[
            ImmediateAction(
                id="act_001",
                type="EMERGENCY_DISPATCH",
                title="Dispatch Ambulances",
                description="Send 2 ambulances immediately to location.",
                agency="Medical Services",
                priority=1,
                estimated_time="5 mins",
                phone_number="108",
                verified=True,
            ),
            ImmediateAction(
                id="act_002",
                type="TRAFFIC_CONTROL",
                title="Secure Area",
                description="Block off the street.",
                agency="Police",
                priority=2,
                estimated_time="10 mins",
                phone_number="100",
                verified=True,
            ),
            ImmediateAction(
                id="act_003",
                type="HOSPITAL_ALERT",
                title="Alert ER",
                description="Prepare 5 beds.",
                agency="Local Hospital",
                priority=3,
                estimated_time="Immediate",
                phone_number=None,
                verified=False,
            ),
        ],
        medical_summary="No known allergies.",
        risk_factors=["Fire", "Traffic"],
        resources_needed=["Ambulance", "Police"],
        followup_actions=["Check on patients tomorrow."],
        search_grounding=None,
        language_detected="English",
        data_quality="HIGH",
    )


@pytest.fixture
def sample_image_b64() -> str:
    """A tiny valid JPEG encoded as a base64 string.

    Returns:
        Base64 payload string.
    """
    # 1x1 pixel JPEG
    return "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA="


@pytest.fixture
def mock_gemini(sample_action_plan: ActionPlan) -> Generator[MagicMock, None, None]:
    """Matches gemini_service with a deterministic canned response.

    Args:
        sample_action_plan: Injected plan model.

    Yields:
        Mocked generator function.
    """
    with patch("services.gemini_service.gemini_service.analyze") as mock_analyze:
        mock_analyze.return_value = sample_action_plan
        yield mock_analyze


@pytest.fixture
def mock_firestore() -> Generator[dict[str, MagicMock], None, None]:
    """Replaces Firestore client with an in-memory dict.

    Yields:
        Dictionary mapping operation to mock.
    """
    with patch("services.firestore_service.firestore_service.log_incident") as log_mock:
        with patch("services.firestore_service.firestore_service.get_recent_incidents") as query_mock:
            with patch("services.firestore_service.firestore_service.delete_incident") as del_mock:
                log_mock.return_value = None
                query_mock.return_value = []
                del_mock.return_value = True
                yield {"log": log_mock, "query": query_mock, "delete": del_mock}


@pytest.fixture
def mock_gcs() -> Generator[MagicMock, None, None]:
    """Replaces GCS client with an in-memory dict.

    Yields:
        Mocked process and upload functionality.
    """
    with patch("services.storage_service.storage_service.process_and_upload_image") as mock_process:
        mock_process.return_value = ("https://mock-gcs/url", b"mockbytes")
        yield mock_process
