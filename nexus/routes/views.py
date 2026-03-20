"""Frontend view routes for NEXUS."""

from flask import Blueprint, render_template

views_bp = Blueprint("views", __name__)

@views_bp.route("/")
def index() -> str:
    """Render the main single-page application."""
    return render_template("index.html")
