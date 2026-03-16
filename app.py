"""
DorkForge - Flask Web Application
===================================

Application factory and entry point for the DorkForge web application.
Supports multi-engine dork query generation with a professional web UI.

Usage:
    python app.py                  # Development server
    gunicorn app:create_app()      # Production server
"""

from flask import Flask

from dorkforge.routes import views_bp, api_bp


def create_app() -> Flask:
    """Application factory: creates and configures the Flask app."""
    app = Flask(__name__)

    # Register blueprints
    app.register_blueprint(views_bp)
    app.register_blueprint(api_bp)

    return app


# Development entry point
app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
