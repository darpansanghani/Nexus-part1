"""Google Cloud Firestore service for NEXUS audit logging."""

import datetime
import logging
from typing import Dict, Any, List, Optional
from flask import Flask
from google.cloud import firestore
from google.api_core.exceptions import GoogleAPIError

logger = logging.getLogger("nexus-app.firestore-service")

class FirestoreService:
    """Manages reading and writing to Firestore."""

    def __init__(self) -> None:
        self._client: firestore.Client | None = None
        self._testing: bool = False
        self._mock_db: Dict[str, Dict[str, Any]] = {"nexus_incidents": {}}

    def init_app(self, app: Flask) -> None:
        """Initialize the Firestore client."""
        self._testing = app.config.get("TESTING", False)
        
        if not self._testing:
            try:
                project_id = app.config.get("GCP_PROJECT_ID")
                # Using native mode implicitly for default DB
                self._client = firestore.Client(project=project_id)
                logger.info("Firestore client initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Firestore client: {e}", exc_info=True)
        else:
            logger.info("Using mock Firestore for testing.")

    def log_incident(self, session_id: str, severity: str, intent: str, confidence: float,
                     actions_count: int, location: str, input_preview: str,
                     processing_time_ms: int, ip_hash: str) -> None:
        """Log an incident to Firestore and update daily metrics."""
        now = datetime.datetime.now(datetime.timezone.utc)
        doc_id = session_id
        
        incident_data = {
            "session_id": session_id,
            "severity": severity,
            "intent": intent,
            "confidence": confidence,
            "actions_count": actions_count,
            "location": location,
            "timestamp": now,
            "input_preview": input_preview[:100],  # Enforce max 100 chars
            "processing_time_ms": processing_time_ms,
            "ip_hash": ip_hash
        }

        if self._testing:
            self._mock_db["nexus_incidents"][doc_id] = incident_data
            return

        if self._client is None:
            logger.warning("Firestore client not initialized. Cannot log incident.")
            return

        try:
            # 1. Write to nexus_incidents
            incidents_ref = self._client.collection("nexus_incidents")
            incidents_ref.document(doc_id).set(incident_data)

            # 2. Update daily aggregates in nexus_metrics
            # Document ID is YYYY-MM-DD
            date_str = now.strftime("%Y-%m-%d")
            metrics_ref = self._client.collection("nexus_metrics").document(date_str)
            
            # Using increment to safely update counters
            metrics_ref.set({
                "total_incidents": firestore.Increment(1),
                f"severity_{severity.lower()}": firestore.Increment(1),
                "last_updated": now
            }, merge=True)
            
        except GoogleAPIError as e:
            logger.error(f"Failed to write to Firestore: {e}", exc_info=True)

    def get_recent_incidents(self, limit: int = 20, severity: str = "") -> List[Dict[str, Any]]:
        """Retrieve recent incidents, optionally filtered by severity."""
        limit = min(limit, 100)
        
        if self._testing:
            results = list(self._mock_db["nexus_incidents"].values())
            if severity:
                results = [r for r in results if r.get("severity") == severity]
            # Simple sorting by mock 'timestamp' if available, otherwise just limit
            return results[:limit]

        if self._client is None:
            return []

        try:
            query = self._client.collection("nexus_incidents")
            
            if severity:
                query = query.where("severity", "==", severity)
                
            # Note: A composite index on severity + timestamp is required 
            # if we filter and order by different fields.
            query = query.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit)
            
            docs = query.stream()
            return [doc.to_dict() for doc in docs]
        except GoogleAPIError as e:
            logger.error(f"Failed to query Firestore: {e}", exc_info=True)
            return []

    def delete_incident(self, session_id: str) -> bool:
        """Delete a log entry for GDPR compliance. Returns True if found and deleted."""
        if self._testing:
            if session_id in self._mock_db["nexus_incidents"]:
                del self._mock_db["nexus_incidents"][session_id]
                return True
            return False

        if self._client is None:
            return False

        try:
            doc_ref = self._client.collection("nexus_incidents").document(session_id)
            doc_snap = doc_ref.get()
            if doc_snap.exists:
                doc_ref.delete()
                return True
            return False
        except GoogleAPIError as e:
            logger.error(f"Failed to delete from Firestore: {e}", exc_info=True)
            return False

# Singleton instance
firestore_service = FirestoreService()

def init_app(app: Flask) -> None:
    firestore_service.init_app(app)
