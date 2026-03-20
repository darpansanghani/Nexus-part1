"""pytest fixtures for NEXUS."""

import pytest
from unittest.mock import patch, MagicMock
from app import create_app
from models.action_plan import ActionPlan, ImmediateAction


@pytest.fixture
def app():
    """Create a testing app instance."""
    app = create_app("testing")
    with app.app_context():
        # Setup mock configurations internally
        pass
    yield app


@pytest.fixture
def client(app):
    """Test client for the app."""
    return app.test_client()


@pytest.fixture
def sample_action_plan():
    """A valid fully-populated ActionPlan dataclass instance."""
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
                verified=True
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
                verified=True
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
                verified=False
            )
        ],
        medical_summary="No known allergies.",
        risk_factors=["Fire", "Traffic"],
        resources_needed=["Ambulance", "Police"],
        followup_actions=["Check on patients tomorrow."],
        search_grounding=None,
        language_detected="English",
        data_quality="HIGH"
    )


@pytest.fixture
def sample_image_b64():
    """A tiny valid JPEG encoded as a base64 string."""
    # 1x1 pixel JPEG
    return "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA="


@pytest.fixture
def mock_gemini(sample_action_plan):
    """Matches gemini_service with a deterministic canned response."""
    with patch("services.gemini_service.GeminiService.analyze") as mock_analyze:
        mock_analyze.return_value = sample_action_plan
        yield mock_analyze


@pytest.fixture
def mock_firestore():
    """Replaces Firestore client with an in-memory dict."""
    with patch("services.firestore_service.FirestoreService.log_incident") as log_mock:
        with patch("services.firestore_service.FirestoreService.get_recent_incidents") as query_mock:
            with patch("services.firestore_service.FirestoreService.delete_incident") as del_mock:
                log_mock.return_value = None
                query_mock.return_value = []
                del_mock.return_value = True
                yield {"log": log_mock, "query": query_mock, "delete": del_mock}


@pytest.fixture
def mock_gcs():
    """Replaces GCS client with an in-memory dict."""
    with patch("services.storage_service.StorageService.process_and_upload_image") as mock_process:
        mock_process.return_value = ("https://mock-gcs/url", b"mockbytes")
        yield mock_process
