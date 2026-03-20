# 🚨 NEXUS — Emergency Response Intelligence Platform

> **AI-powered multi-modal emergency analysis system for India.**  
> Transforms unstructured inputs — voice transcripts, images, medical records, weather feeds — into structured, actionable emergency response plans in real time.

[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-black?logo=flask)](https://flask.palletsprojects.com)
[![Gemini](https://img.shields.io/badge/Gemini-1.5--Pro-orange?logo=google)](https://deepmind.google/technologies/gemini/)
[![Cloud Run](https://img.shields.io/badge/Cloud%20Run-Deployed-brightgreen?logo=googlecloud)](https://cloud.google.com/run)
[![License](https://img.shields.io/badge/License-MIT-lightgrey)](LICENSE)

---

## 🌐 Live Deployment

| Environment | URL |
|---|---|
| **Production** | [https://nexus-app-pyjvtbj3na-ew.a.run.app](https://nexus-app-pyjvtbj3na-ew.a.run.app) |
| **Health Check** | [/api/health](https://nexus-app-pyjvtbj3na-ew.a.run.app/api/health) |
| **GCP Console** | [Cloud Run → nexus-app](https://console.cloud.google.com/run/detail/europe-west1/nexus-app?project=promptwars-part1) |

---

## 🧠 What is NEXUS?

NEXUS is an intelligent emergency coordination system built specifically for the Indian context. It ingests **any** unstructured emergency signal — a panicked voice call, a blurry accident photo, a garbled medical record, a flood situation report — and instantly produces a structured, prioritised action plan complete with:

- 🚑 **Who to call** (108 ambulance, 100 police, 101 fire, 1091 women helpline)
- ⚡ **What to do** — ordered by priority, with estimated response times
- 💊 **Medical triage** — drug interaction checks, allergy flags, contraindications
- 🗺️ **Location detection** — nearest hospitals, police stations, NDRF camps
- ⚠️ **Risk assessment** — fire hazard, chemical spill, crowd crush, flood escalation
- 🔍 **Real-time grounding** — live search results embedded into the response
- 🌐 **Multilingual** — handles Hindi, Telugu, Tamil, English, and mixed-language inputs

### 🎯 Why it matters

India handles millions of emergency calls annually across 112. Most are in regional languages, many come with images or partial information, and first responders need structured guidance **in seconds**. NEXUS bridges that gap using AI.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    NEXUS Platform                       │
│                                                         │
│  ┌──────────┐    ┌─────────────────────────────────┐   │
│  │  Browser │───▶│   Flask Application (Gunicorn)   │   │
│  │   (SPA)  │    │                                 │   │
│  └──────────┘    │  ┌──────────────────────────┐   │   │
│                  │  │   Rate Limiter (Sliding   │   │   │
│                  │  │      Window, per-IP)      │   │   │
│                  │  └────────────┬─────────────┘   │   │
│                  │               │                  │   │
│                  │  ┌────────────▼─────────────┐   │   │
│                  │  │  Input Validator          │   │   │
│                  │  │  (bleach, regex, b64)     │   │   │
│                  │  └────────────┬─────────────┘   │   │
│                  │               │                  │   │
│                  │  ┌────────────▼──────────────┐  │   │
│                  │  │   API Routes (/analyze,   │  │   │
│                  │  │   /health, /log, /demo)   │  │   │
│                  │  └────────────┬──────────────┘  │   │
│                  │               │                  │   │
│                  └───────────────┼──────────────────┘   │
│                                  │                      │
│         ┌────────────────────────┼───────────────────┐  │
│         │                        │                   │  │
│  ┌──────▼──────┐   ┌─────────────▼──────┐  ┌──────┐ │  │
│  │  Gemini 1.5 │   │  Cloud Firestore   │  │ GCS  │ │  │
│  │  Pro + Search│  │  (incident logging)│  │(imgs)│ │  │
│  └─────────────┘   └────────────────────┘  └──────┘ │  │
│                                                      │  │
│  ┌────────────────────────────────────────────────┐  │  │
│  │        Secret Manager (API key storage)        │  │  │
│  └────────────────────────────────────────────────┘  │  │
└─────────────────────────────────────────────────────────┘
```

---

## 🛠️ Technology Stack

### Backend

| Layer | Technology | Purpose |
|---|---|---|
| **Web Framework** | [Flask 3.x](https://flask.palletsprojects.com) | Lightweight WSGI app, blueprint routing |
| **WSGI Server** | [Gunicorn](https://gunicorn.org) | Production-grade multi-threaded server |
| **AI Engine** | [Gemini 1.5 Pro](https://deepmind.google/technologies/gemini/) | Multi-modal emergency analysis, JSON output |
| **Search Grounding** | [Google Search Retrieval](https://ai.google.dev) | Real-time info embedded into AI responses |
| **Image Processing** | [Pillow (PIL)](https://pillow.readthedocs.io) | Resize, convert, strip EXIF metadata |
| **Input Sanitization** | [bleach](https://bleach.readthedocs.io) | HTML/XSS sanitization |
| **Database** | [Cloud Firestore](https://firebase.google.com/docs/firestore) | NoSQL incident and metrics logging |
| **Object Storage** | [Cloud Storage (GCS)](https://cloud.google.com/storage) | Secure image upload with signed URLs |
| **Secret Management** | [Secret Manager](https://cloud.google.com/secret-manager) | API key storage, never hardcoded |
| **Deployment** | [Cloud Run](https://cloud.google.com/run) | Serverless containers, auto-scaling |

### Frontend

| Technology | Purpose |
|---|---|
| **Vanilla HTML/CSS/JS** | Single-page application (SPA) |
| **Google Maps API** | Real-time location rendering |
| **Chart.js** | Metrics and analytics visualisation |
| **Web Speech API** | Voice input transcription (browser-native) |

### Code Quality & Testing

| Tool | Purpose |
|---|---|
| **Ruff** | Linting + auto-formatting (replaces flake8, isort, black) |
| **Mypy** (`--strict`) | Static type checking |
| **Bandit** | Security vulnerability scanning |
| **Pytest + pytest-cov** | Unit & integration tests, 85%+ coverage required |

---

## 📁 Project Structure

```
nexus/
├── app.py                    # Flask application factory
├── config.py                 # Environment-based configuration
├── constants.py              # Centralised magic values
├── exceptions.py             # Custom exception hierarchy
├── logger.py                 # Structured JSON logging
├── wsgi.py                   # Gunicorn entrypoint
├── Dockerfile                # Container build definition
├── requirements.txt          # Production dependencies
├── requirements-dev.txt      # Dev/test dependencies
│
├── middleware/
│   ├── input_validator.py    # Text/image sanitization & validation
│   ├── rate_limiter.py       # Sliding window rate limiting (per IP)
│   └── security_headers.py  # CSP, HSTS, X-Frame security headers
│
├── models/
│   └── action_plan.py        # ActionPlan & ImmediateAction dataclasses
│
├── routes/
│   ├── api.py                # /api/analyze, /api/health, /api/log, /api/demo
│   └── views.py              # Frontend SPA route
│
├── services/
│   ├── gemini_service.py     # Gemini AI analysis + retry logic
│   ├── firestore_service.py  # Incident & metrics logging to Firestore
│   ├── secret_service.py     # Secret Manager + env var fallback
│   └── storage_service.py    # Image upload to GCS + signed URLs
│
├── static/
│   ├── css/nexus.css         # Application stylesheet
│   └── js/                   # Frontend JS modules
│       ├── app.js            # Main SPA logic
│       ├── charts.js         # Analytics charts
│       ├── maps.js           # Google Maps integration
│       └── voice.js          # Voice input handling
│
├── templates/
│   └── index.html            # Single-page app shell
│
└── tests/
    ├── conftest.py           # Shared fixtures and mocks
    ├── test_api.py           # API endpoint integration tests
    ├── test_gemini_service.py# Gemini service unit tests
    ├── test_models.py        # Data model validation tests
    ├── test_rate_limiter.py  # Rate limiting logic tests
    └── test_validator.py     # Input sanitization tests
```

---

## 🚀 API Endpoints

### `POST /api/analyze`
Core analysis endpoint. Accepts text, image, or both.

**Request:**
```json
{
  "text": "Vehicle overturned on NH48. Petrol leaking. Child trapped.",
  "image": "data:image/jpeg;base64,/9j/...",
  "context": "Optional metadata"
}
```

**Response:**
```json
{
  "intent": "Road accident with fire risk and trapped child",
  "severity": "CRITICAL",
  "confidence": 0.96,
  "location": "NH48, near Hitec City flyover",
  "affected_people": "1 child trapped, 2 adults injured",
  "immediate_actions": [
    {
      "id": "act_001",
      "type": "EMERGENCY_DISPATCH",
      "title": "Dispatch Fire Brigade for fuel leak",
      "agency": "Fire Services",
      "priority": 1,
      "estimated_time": "4 minutes",
      "phone_number": "101",
      "verified": true
    }
  ],
  "medical_summary": null,
  "risk_factors": ["Fuel leak", "Fire risk", "Traffic blockage"],
  "resources_needed": ["Fire engine", "Ambulance", "Jaws of Life"],
  "followup_actions": ["Traffic diversion on NH48"],
  "search_grounding": "Apollo Hospital 2.3km, Care Hospital 4.1km",
  "language_detected": "English",
  "data_quality": "HIGH"
}
```

### `GET /api/health`
System health check including Gemini and Firestore availability.

### `GET /api/demo`
Returns 5 pre-built demo scenarios (road accident, cardiac, flood, mental health, air quality).

### `GET /api/log?limit=20&severity=HIGH`
Retrieve recent incidents. Filterable by severity.

### `DELETE /api/log/<session_id>`
GDPR-compliant incident deletion.

---

## ⚙️ Security Features

- **Rate Limiting** — Sliding window, per-IP-hash, 10 req/min on `/analyze`
- **IP Hashing** — Client IPs are SHA-256 hashed before logging (GDPR compliant)
- **Input Sanitization** — bleach strips HTML, regex blocks SQL injection, null bytes rejected
- **Image Security** — EXIF stripped, resized, format-validated before upload
- **Secret Management** — All API keys in Cloud Secret Manager, never in code or env files
- **Security Headers** — CSP, HSTS, X-Frame-Options, Referrer-Policy on every response
- **Signed URLs** — GCS objects served via time-limited signed URLs

---

## 🏃 Running Locally

### Prerequisites
- Python 3.12+
- Google Cloud SDK authenticated (`gcloud auth application-default login`)
- A Gemini API key from [Google AI Studio](https://aistudio.google.com)

### Setup

```bash
# Clone and enter the project
cd nexus/

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Copy and fill in environment variables
cp .env.example .env
# Edit .env with your keys

# Run the development server
flask --app app run --debug
```

### Environment Variables (`.env`)

```env
FLASK_ENV=development
PORT=8080
GCP_PROJECT_ID=your-gcp-project-id
GEMINI_API_KEY=your-gemini-api-key
MAPS_API_KEY=your-maps-api-key
GCS_BUCKET_NAME=nexus-uploads
USE_SECRET_MANAGER=false
LOG_LEVEL=INFO
```

---

## 🧪 Running Tests

```bash
# Run full test suite with coverage
pytest --cov=. --cov-report=term-missing

# Run only specific test modules
pytest tests/test_api.py -v
pytest tests/test_validator.py -v

# Run all audit tools
ruff check .            # Linting
mypy . --strict         # Type checking
bandit -r . -ll         # Security scan
```

---

## 🌍 Deployment (Cloud Run)

The application deploys automatically to Google Cloud Run:

```bash
# Authenticate
gcloud auth login
gcloud config set project promptwars-part1

# Create secrets (first time only)
echo "YOUR_GEMINI_KEY" | gcloud secrets create nexus-gemini-api-key --data-file=-
echo "YOUR_MAPS_KEY"   | gcloud secrets create nexus-maps-api-key --data-file=-

# Deploy
gcloud run deploy nexus-app \
  --source . \
  --region europe-west1 \
  --allow-unauthenticated
```

---

## 📊 Demo Scenarios

NEXUS ships with 5 built-in emergency scenarios to demonstrate capabilities:

| # | Scenario | Category |
|---|---|---|
| 1 | Multi-vehicle road accident (NH48, Hyderabad) | Emergency |
| 2 | Elderly cardiac patient with drug interactions | Medical |
| 3 | Flood disaster coordination (Warangal, 2300 families) | Disaster |
| 4 | Mental health crisis — 2AM WhatsApp message | Mental Health |
| 5 | Severe air quality event (Delhi AQI 487) | Public Health |

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

*Built for PromptWar Part 1 — AI-powered emergency response for India* 🇮🇳
