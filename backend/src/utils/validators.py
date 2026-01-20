"""
Input validation utilities for API request data.
Ensures data integrity and security before processing.
"""

import re
from datetime import datetime
from typing import Dict, Any, List, Optional


# Allowed values for enum-like fields
VALID_STATUSES = {'pending', 'in_progress', 'completed'}
VALID_PRIORITIES = {'low', 'medium', 'high', 'urgent'}


def validate_task_data(data: Dict[str, Any], required_fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Validate task creation/update data.
    
    Args:
        data: Dictionary containing task fields from request
        required_fields: List of required field names (None for updates)
        
    Returns:
        dict: Validated and sanitized data
        
    Raises:
        ValueError: If validation fails with descriptive error message
    """
    errors = []
    
    # Check required fields for creation
    if required_fields:
        for field in required_fields:
            if field not in data or not data[field]:
                errors.append(f"Field '{field}' is required")
    
    # Validate title (if present)
    if 'title' in data:
        title = data['title'].strip()
        if not title:
            errors.append("Title cannot be empty")
        elif len(title) > 200:
            errors.append("Title cannot exceed 200 characters")
        data['title'] = title  # Use sanitized version
    
    # Validate description (if present)
    if 'description' in data and data['description']:
        data['description'] = data['description'].strip()
    
    # Validate status (if present)
    if 'status' in data:
        status = data['status'].lower().strip()
        if status not in VALID_STATUSES:
            errors.append(f"Status must be one of: {', '.join(VALID_STATUSES)}")
        data['status'] = status
    
    # Validate priority (if present)
    if 'priority' in data:
        priority = data['priority'].lower().strip()
        if priority not in VALID_PRIORITIES:
            errors.append(f"Priority must be one of: {', '.join(VALID_PRIORITIES)}")
        data['priority'] = priority
    
    # Validate category (if present)
    if 'category' in data and data['category']:
        category = data['category'].strip()
        if len(category) > 50:
            errors.append("Category cannot exceed 50 characters")
        data['category'] = category
    
    # Validate due_date (if present)
    if 'due_date' in data and data['due_date']:
        try:
            # Accept ISO 8601 format: 2024-12-31T23:59:59
            if isinstance(data['due_date'], str):
                data['due_date'] = datetime.fromisoformat(data['due_date'].replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            errors.append("Invalid due_date format. Use ISO 8601 (e.g., 2024-12-31T23:59:59)")
    
    # Validate assigned_to (if present) - must be positive integer
    if 'assigned_to' in data and data['assigned_to'] is not None:
        try:
            assigned_to = int(data['assigned_to'])
            if assigned_to <= 0:
                errors.append("assigned_to must be a positive integer")
            data['assigned_to'] = assigned_to
        except (ValueError, TypeError):
            errors.append("assigned_to must be a valid user ID (integer)")
    
    # If any validation errors, raise exception with all messages
    if errors:
        raise ValueError('; '.join(errors))
    
    return data


def validate_email(email: str) -> bool:
    """
    Validate email format using regex.
    
    Args:
        email: Email address to validate
        
    Returns:
        bool: True if valid email format
    """
    # Basic email regex pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_user_data(data: Dict[str, Any], is_update: bool = False) -> Dict[str, Any]:
    """
    Validate user registration/update data.
    
    Args:
        data: Dictionary containing user fields
        is_update: True if updating existing user (makes fields optional)
        
    Returns:
        dict: Validated and sanitized data
        
    Raises:
        ValueError: If validation fails
    """
    errors = []
    
    # Required fields for registration
    if not is_update:
        required_fields = ['username', 'email', 'password']
        for field in required_fields:
            if field not in data or not data[field]:
                errors.append(f"Field '{field}' is required")
    
    # Validate username
    if 'username' in data:
        username = data['username'].strip()
        if len(username) < 3:
            errors.append("Username must be at least 3 characters")
        elif len(username) > 80:
            errors.append("Username cannot exceed 80 characters")
        elif not re.match(r'^[a-zA-Z0-9_-]+$', username):
            errors.append("Username can only contain letters, numbers, hyphens, and underscores")
        data['username'] = username
    
    # Validate email
    if 'email' in data:
        email = data['email'].strip().lower()
        if not validate_email(email):
            errors.append("Invalid email format")
        data['email'] = email
    
    # Validate password (only check if provided)
    if 'password' in data and data['password']:
        password = data['password']
        if len(password) < 8:
            errors.append("Password must be at least 8 characters")
        elif len(password) > 128:
            errors.append("Password cannot exceed 128 characters")
        # Don't sanitize password - preserve exactly as entered
    
    # Validate names if provided
    for field in ['first_name', 'last_name']:
        if field in data and data[field]:
            name = data[field].strip()
            if len(name) > 50:
                errors.append(f"{field.replace('_', ' ').title()} cannot exceed 50 characters")
            data[field] = name
    
    if errors:
        raise ValueError('; '.join(errors))
    
    return data