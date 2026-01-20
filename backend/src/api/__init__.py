"""
API Package Initialization Module

This module creates the main API blueprint that serves as the entry point
for all API routes in the application. All route modules are imported here
and registered to the blueprint.

Blueprint Pattern Benefits:
- Modular route organization
- URL prefix management (/api for all routes)
- Easy route registration and discovery
- Better code organization and scalability
"""

from flask import Blueprint

# Create the main API blueprint with URL prefix '/api'
# This means all routes registered to this blueprint will be prefixed with /api
# Example: A route '/tasks' becomes '/api/tasks'
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Import route modules to register them with the blueprint
# The imports must come AFTER blueprint creation to avoid circular imports
from backend.src.api import task_routes  # Task management endpoints

# TODO: Uncomment when user routes are created
# from backend.src.api import user_routes  # Authentication and user management endpoints

# Export the blueprint so it can be imported by app.py
# This allows the main Flask app to register all API routes at once
__all__ = ['api_bp']