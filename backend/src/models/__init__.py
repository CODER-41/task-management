"""
Models package initialization.
Centralizes all database models for easy import.
"""

from backend.src.models.task import Task
from backend.src.models.user import User

# Export all models for easy access
__all__ = ['Task', 'User']