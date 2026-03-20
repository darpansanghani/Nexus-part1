import os
from dotenv import load_dotenv
from app import create_app

# Load environment variables from .env.example (contains real keys for Cloud Run)
# Falls back gracefully if the file doesn't exist
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env.example"), override=False)

# Create the application instance for Gunicorn
env_name = os.environ.get("FLASK_ENV", "production")
app = create_app(env_name)

