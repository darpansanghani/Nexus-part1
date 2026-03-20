import os
from app import create_app

# Create the application instance for Gunicorn
env_name = os.environ.get("FLASK_ENV", "production")
app = create_app(env_name)
