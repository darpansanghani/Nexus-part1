"""API routes for NEXUS."""

import datetime
import time
from flask import Blueprint, jsonify, request, g, current_app

from exceptions import ValidationError
from middleware.input_validator import sanitize_text, validate_image
from middleware.rate_limiter import rate_limit, get_ip_hash
from services.firestore_service import firestore_service
from services.gemini_service import gemini_service
from services.secret_service import secret_service
from services.storage_service import storage_service

api_bp = Blueprint("api", __name__, url_prefix="/api")

# Pre-built demo scenarios
DEMO_SCENARIOS = [
    {
        "id": "road_accident",
        "title": "Multi-casualty road accident",
        "icon": "🚑",
        "category": "Emergency",
        "input": "TRAFFIC CAM ALERT - NH48 Hyderabad near Hitec City flyover 17:43 IST.\n"
                 "Multiple vehicles involved. Truck overturned. 3 cars visible damage.\n"
                 "Witness call: 'aadmi bahar gira hai, khoon aa raha hai, ek bachcha bhi hai \n"
                 "andar, traffic jam ho raha hai, petrol smell aa raha hai'.\n"
                 "Weather: Heavy rain, visibility 40m, road slippery.\n"
                 "Nearby: Apollo Hospital 2.3km, Care Hospital 4.1km, Police Station 0.8km.\n"
                 "Traffic density: HIGH. Peak hour.",
        "description": "A complex multi-vehicle accident with trapped victims and fire risk."
    },
    {
        "id": "medical_triage",
        "title": "Elderly cardiac patient crisis",
        "icon": "🏥",
        "category": "Medical",
        "input": "PATIENT INTAKE - Emergency. Krishnamurthy, 72M.\n"
                 "Severe chest pain, dizziness, left arm numbness for 30 minutes.\n"
                 "BP: 180/110, HR: 45 bpm irregular, SpO2: 91%.\n"
                 "Medications from crumpled paper: Warfarin 5mg OD, Metformin 500mg BD,\n"
                 "Atorvastatin 40mg, Aspirin 75mg (already took today at 6am).\n"
                 "Allergies: penicillin causes rash, sulfa drugs.\n"
                 "History: DM Type 2, Hypertension, Atrial Fibrillation, CABG 2019.\n"
                 "Son arriving in 30 minutes. Insurance: CGHS.",
        "description": "Critical medical emergency requiring medication interaction checks."
    },
    {
        "id": "flood_disaster",
        "title": "Flood disaster coordination",
        "icon": "🌊",
        "category": "Disaster",
        "input": "NDRF SITUATION REPORT - Warangal District 14:00 IST.\n"
                 "Rainfall last 24hr: 380mm. Godavari: 12.3m above danger level, rising 8cm/hr.\n"
                 "Flooded: Hanamkonda wards 4, 7, 12 — 2300 families estimated.\n"
                 "CRITICAL: Nursing home with 45 elderly residents TRAPPED.\n"
                 "Generator fuel: 4 hours remaining.\n"
                 "Road access: NH163 blocked, SH4 partially open.\n"
                 "NDRF boats available: 6 total, 2 already deployed.\n"
                 "Helicopter pad: Collectorate, 2km from nursing home.\n"
                 "Mobile: Airtel down in ward 7, BSNL operational.",
        "description": "Large-scale disaster with trapped vulnerable citizens."
    },
    {
        "id": "mental_health",
        "title": "Mental health crisis — night",
        "icon": "💙",
        "category": "Mental Health",
        "input": "VOICE TRANSCRIPT — WhatsApp message received by iCall helpline:\n"
                 "'yaar mujhe pata nahi kya ho raha hai main bohot tired hoon sab se \n"
                 "college mein fail ho gaya ghar pe pata chala papa ne baat karna band kar diya \n"
                 "3 din se kuch nahi khaya so nahi pa raha mera phone bhi band hone wala hai \n"
                 "isliye message kar raha hoon mujhe lagta hai actually chhodo'\n"
                 "Message time: 02:17 AM. User last location: Pune, Maharashtra.",
        "description": "Urgent psychological crisis requiring immediate intervention."
    },
    {
        "id": "air_quality",
        "title": "Severe air quality public health event",
        "icon": "🌫️",
        "category": "Public Health",
        "input": "CPCB AGGREGATED ALERT - Delhi NCR 08:00 IST.\n"
                 "AQI: Anand Vihar 487 Severe+, RK Puram 412, ITO 398, Rohini 445.\n"
                 "PM2.5: 340 micrograms per cubic meter against limit of 60.\n"
                 "Wind: 2 km/h near-calm. Temperature inversion ceiling: 200m.\n"
                 "Hospitals: 340 percent spike in respiratory OPD since 6am.\n"
                 "High risk population: 180000 elderly and 90000 asthma patients on CGHS.\n"
                 "IGI Airport visibility: 200m. Active stubble fires: 847 detected by satellite.",
        "description": "City-wide environmental crisis impacting vulnerable populations."
    }
]


@api_bp.route("/health", methods=["GET"])
def health_check() -> tuple:
    """System health check endpoint."""
    # Basic availability checks
    gemini_available = True
    firestore_available = True
    
    # Check Gemini config
    if not current_app.config.get("TESTING") and not secret_service.get_secret("nexus-gemini-api-key"):
        gemini_available = False

    # Check Firestore
    if not current_app.config.get("TESTING") and getattr(firestore_service, "_client", None) is None:
        firestore_available = False

    status = "healthy" if (gemini_available and firestore_available) else "degraded"
    status_code = 200 if status == "healthy" else 503

    return jsonify({
        "status": status,
        "version": "1.0.0",
        "gemini_available": gemini_available,
        "firestore_available": firestore_available,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }), status_code


@api_bp.route("/demo", methods=["GET"])
def demo_scenarios() -> tuple:
    """Return pre-built demo scenarios."""
    response = jsonify({"scenarios": DEMO_SCENARIOS})
    response.headers["Cache-Control"] = "public, max-age=3600"
    return response, 200


@api_bp.route("/analyze", methods=["POST"])
@rate_limit(limit=10, window_seconds=60, endpoint_name="analyze")
def analyze() -> tuple:
    """Core analysis endpoint."""
    data = request.get_json(silent=True) or {}
    
    raw_text = data.get("text", "")
    raw_image = data.get("image", "")
    context = data.get("context", "")

    if not raw_text and not raw_image:
        raise ValidationError("Must provide either text or image input.")

    # 1. Validation and sanitization
    safe_text = sanitize_text(raw_text) if raw_text else None
    safe_context = sanitize_text(context) if context else None
    
    # 2. Image processing
    processed_image_bytes = None
    if raw_image:
        image_bytes = validate_image(raw_image)
        # Uploads to GCS, returns signed URL (not strictly used by processing if we pass bytes to Gemini directly)
        signed_url, processed_image_bytes = storage_service.process_and_upload_image(image_bytes)
        # We could append the signed URL to context if needed later, but we pass bytes directly to Gemini
        if safe_context:
            safe_context += f" [Attached Image: {signed_url}]"
        else:
            safe_context = f"[Attached Image: {signed_url}]"

    # 3 & 4. Gemini Analysis
    action_plan = gemini_service.analyze(
        text=safe_text, 
        image_bytes=processed_image_bytes, 
        context=safe_context
    )

    # 5 & 6. Logging
    duration_ms = int((time.time() - getattr(g, "start_time", time.time())) * 1000)
    client_ip = request.remote_addr or request.headers.get("X-Forwarded-For", "0.0.0.0")
    ip_hash = get_ip_hash(client_ip)
    
    input_preview = safe_text if safe_text else "Image upload"
    
    firestore_service.log_incident(
        session_id=g.session_id,
        severity=action_plan.severity,
        intent=action_plan.intent,
        confidence=action_plan.confidence,
        actions_count=len(action_plan.immediate_actions),
        location=action_plan.location,
        input_preview=input_preview,
        processing_time_ms=duration_ms,
        ip_hash=ip_hash
    )

    # 7. Response
    response = jsonify(action_plan.to_dict())
    response.headers["X-Session-ID"] = g.session_id
    response.headers["X-Processing-Time"] = str(duration_ms)
    response.headers["X-Confidence"] = str(action_plan.confidence)
    response.headers["Cache-Control"] = "no-store"

    return response, 200


@api_bp.route("/log", methods=["GET"])
def get_logs() -> tuple:
    """Retrieve recent incidents."""
    try:
        limit = int(request.args.get("limit", 20))
    except ValueError:
        limit = 20
        
    severity = request.args.get("severity", "")
    
    incidents = firestore_service.get_recent_incidents(limit=limit, severity=severity)
    return jsonify({
        "incidents": incidents,
        "total": len(incidents)
    }), 200


@api_bp.route("/log/<session_id>", methods=["DELETE"])
def delete_log(session_id: str) -> tuple:
    """Delete a specific log entry (GDPR)."""
    success = firestore_service.delete_incident(session_id)
    if success:
        return "", 204
    else:
        return jsonify({"error": "Log entry not found"}), 404
