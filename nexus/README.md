# NEXUS | Emergency AI Triage

NEXUS is a production-ready, Gemini-powered web application that acts as a universal bridge between human intent and complex emergency/societal systems. It ingests messy unstructured real-world data (photos, voice transcripts, emergency reports) and uses Gemini 1.5 Pro to return a structured, verified, prioritized action plan in seconds, thereby saving critical time during emergencies.

## Prerequisites

- Python 3.12
- `pip`
- Google Cloud project with billing enabled
- Gemini API key from Google AI Studio
- `gcloud` CLI installed and authenticated via `gcloud auth application-default login`

## Environment Setup

1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd nexus
   ```

2. **Set up the virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and set:
   - `GEMINI_API_KEY`
   - `GCP_PROJECT_ID`
   - `GCS_BUCKET_NAME`
   - `FLASK_ENV=development`

## Running Locally

To start the application locally:
```bash
python app.py
```
The application will be available at [http://localhost:8080](http://localhost:8080).

## Running Tests

Run the full pytest suite with coverage reporting:
```bash
pytest -v --cov=. --cov-report=term-missing
```
*Expected: all tests pass, coverage above 85%. (No real GCP credentials required, everything is mocked).*

## Running Linters

Ensure code quality by running these tools:
```bash
ruff check .
mypy . --strict
bandit -r . -ll
```

## Architecture Diagram

```text
 Browser / Client 
       │
       ▼
   [ Flask App (app.py) ]
       │                      ┌─────────────────┐
       ├─► [ Rate Limiter ] ──► [ Input Validator]
       │                      └─────────────────┘
       ▼
 [ Gemini Service ] ──► (Gemini 1.5 Pro via google-generativeai)
       │
       ├─► [ Storage Service ] ──► (GCS bucket pre-processing & image upload)
       │
       ▼
 [ Firestore Service ] ──► (Audit Logging to nexus_incidents & metrics)
       │
       ▼
   Response JSON Action Plan
```

## API Reference

| Method | Path               | Description                                  | Request Body                       | Response Fields                     |
|--------|--------------------|----------------------------------------------|------------------------------------|-------------------------------------|
| POST   | `/api/analyze`     | Core analysis endpoint returning action plan | `text`, `image` (b64), `context`   | ActionPlan schema JSON              |
| GET    | `/api/health`      | System health check                          | None                               | `status`, `version`, `timestamp`    |
| GET    | `/api/demo`        | Pre-built demo scenarios                     | None                               | `{ scenarios: [...] }`              |
| GET    | `/api/log`         | Retrieve recent incident logs                | Query: `limit`, `severity`         | `{ incidents: [...], total: int }`  |
| DELETE | `/api/log/<id>`    | Delete a specific log entry (GDPR)           | None                               | `204 No Content`                    |

## Google Services Used

| Service | Purpose |
|---------|---------|
| **Gemini 1.5 Pro** | Core AI multimodal analysis engine mapping unstructured data to JSON arrays |
| **Cloud Firestore** | Audit logging of incidents and daily aggregation metrics |
| **Cloud Storage** | Secure handling and storage of uploaded photos (re-encoded via Pillow) |
| **Secret Manager** | Secure storage and runtime fetching of API keys |
| **Maps JavaScript API** | Visualizing incident location and nearby hospitals |
| **Google Charts API** | Dynamic visualizations of confidence scores and action priorities |
| **Cloud Logging** | Structured JSON server-side logging for operational metrics |
| **Google Fonts** | Highly legible typography (`DM Sans`, `DM Mono`, `Material Symbols`) |

---
**Deployment is handled separately via Cloud Run MCP. This repository contains application code only.**
