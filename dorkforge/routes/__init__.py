"""
DorkForge - Route Registration
================================

Registers all Flask blueprints for the application.
"""

from dorkforge.routes.views import views_bp
from dorkforge.routes.api import api_bp

__all__ = ["views_bp", "api_bp"]
