"""
Task API Routes - RESTful Endpoints for Task Management

This module defines all HTTP endpoints for task operations following REST conventions:
- POST   /api/tasks          → Create new task
- GET    /api/tasks          → List all tasks (with filtering & pagination)
- GET    /api/tasks/<id>     → Get single task by ID
- PUT    /api/tasks/<id>     → Update existing task
- DELETE /api/tasks/<id>     → Delete task
- GET    /api/tasks/search   → Search tasks by keyword

Authentication:
All endpoints require a valid JWT token in the Authorization header:
    Authorization: Bearer <your-jwt-token>

Response Format:
All responses are JSON with consistent structure:
    Success: { "message": "...", "task": {...} } or { "tasks": [...] }
    Error:   { "error": "Error message" }

HTTP Status Codes:
    200 - Success (GET, PUT, DELETE)
    201 - Created (POST)
    400 - Bad Request (validation errors)
    401 - Unauthorized (missing/invalid JWT)
    403 - Forbidden (permission denied)
    404 - Not Found
    500 - Internal Server Error
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.src.api import api_bp
from backend.src.services.task_service import TaskService


# ============================================================================
# CREATE TASK ENDPOINT
# ============================================================================

@api_bp.route('/tasks', methods=['POST'])
@jwt_required()  # Decorator ensures valid JWT token is present
def create_task():
    """
    Create a new task in the system.
    
    Authentication Required: Yes (JWT token)
    
    Request Headers:
        Authorization: Bearer <jwt-token>
    
    Request Body (JSON):
        {
            "title": "Complete project proposal",           # Required, max 200 chars
            "description": "Detailed task description",     # Optional
            "status": "pending",                            # Optional: pending|in_progress|completed
            "priority": "high",                             # Optional: low|medium|high|urgent
            "category": "Work",                             # Optional, max 50 chars
            "due_date": "2024-12-31T23:59:59",             # Optional, ISO 8601 format
            "assigned_to": 5                                # Optional, user ID (integer)
        }
    
    Success Response (201):
        {
            "message": "Task created successfully",
            "task": {
                "id": 1,
                "title": "Complete project proposal",
                "description": "Detailed task description",
                "status": "pending",
                "priority": "high",
                "category": "Work",
                "due_date": "2024-12-31T23:59:59",
                "assigned_to": 5,
                "assignee": {
                    "id": 5,
                    "username": "john_doe",
                    "email": "john@example.com"
                },
                "created_by": 1,
                "creator": {
                    "id": 1,
                    "username": "admin",
                    "email": "admin@example.com"
                },
                "created_at": "2024-01-15T10:30:00",
                "updated_at": "2024-01-15T10:30:00"
            }
        }
    
    Error Responses:
        400 - Validation error (e.g., missing title, invalid status)
        401 - Missing or invalid JWT token
        404 - Assigned user not found
        500 - Server error
    """
    try:
        # Extract the authenticated user's ID from the JWT token payload
        # This was set during login and is cryptographically verified
        current_user_id = get_jwt_identity()
        
        # Parse JSON data from request body
        # Returns None if body is empty or not valid JSON
        data = request.get_json()
        
        # Validate that request body contains data
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Delegate task creation to service layer
        # Service handles validation, database operations, and business logic
        task = TaskService.create_task(data, created_by_id=current_user_id)
        
        # Return success response with 201 Created status
        # to_dict() converts SQLAlchemy model to JSON-serializable dictionary
        return jsonify({
            'message': 'Task created successfully',
            'task': task.to_dict()
        }), 201
        
    except ValueError as e:
        # Validation errors from validators or service layer
        # Examples: empty title, invalid status, user not found
        return jsonify({'error': str(e)}), 400
    
    except Exception as e:
        # Catch-all for unexpected errors (database connection, etc.)
        # In production, log this error to monitoring system
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500


# ============================================================================
# LIST TASKS ENDPOINT (with filtering and pagination)
# ============================================================================

@api_bp.route('/tasks', methods=['GET'])
@jwt_required()
def get_tasks():
    """
    Retrieve a paginated list of tasks with optional filtering.
    
    Authentication Required: Yes (JWT token)
    
    Query Parameters (all optional):
        status       - Filter by status (pending|in_progress|completed)
        priority     - Filter by priority (low|medium|high|urgent)
        category     - Filter by category name
        assigned_to  - Filter by assignee user ID (integer)
        my_tasks     - If 'true', show only current user's tasks (created by OR assigned to)
        page         - Page number (default: 1, 1-indexed)
        per_page     - Items per page (default: 20, max: 100)
    
    Example Requests:
        GET /api/tasks                              → All tasks, page 1
        GET /api/tasks?status=pending               → Only pending tasks
        GET /api/tasks?my_tasks=true                → Only my tasks
        GET /api/tasks?priority=high&page=2         → High priority tasks, page 2
        GET /api/tasks?assigned_to=5&per_page=50    → Tasks assigned to user 5, 50 per page
    
    Success Response (200):
        {
            "tasks": [
                {
                    "id": 1,
                    "title": "Task 1",
                    "status": "pending",
                    // ... full task object
                },
                {
                    "id": 2,
                    "title": "Task 2",
                    "status": "in_progress",
                    // ... full task object
                }
            ],
            "total": 45,        # Total number of matching tasks (all pages)
            "page": 1,          # Current page number
            "per_page": 20,     # Items per page
            "pages": 3          # Total number of pages
        }
    
    Error Responses:
        401 - Missing or invalid JWT token
        500 - Server error
    """
    try:
        # Get authenticated user ID from JWT
        current_user_id = get_jwt_identity()
        
        # Extract and parse query parameters from URL
        # request.args is a MultiDict of query string parameters
        
        # Filter parameters (optional, None if not provided)
        status = request.args.get('status')          # e.g., ?status=pending
        priority = request.args.get('priority')      # e.g., ?priority=high
        category = request.args.get('category')      # e.g., ?category=Work
        assigned_to = request.args.get('assigned_to', type=int)  # Auto-convert to int
        
        # Special filter: show only current user's tasks
        # Convert string 'true'/'false' to boolean
        my_tasks = request.args.get('my_tasks', 'false').lower() == 'true'
        
        # Pagination parameters with defaults and type conversion
        page = request.args.get('page', 1, type=int)           # Default to page 1
        per_page = request.args.get('per_page', 20, type=int)  # Default to 20 items
        
        # Security: Cap per_page at 100 to prevent abuse/performance issues
        # min() ensures we never exceed 100 items per page
        per_page = min(per_page, 100)
        
        # Determine user filter based on my_tasks parameter
        # If my_tasks=true, filter by current user; otherwise show all tasks
        user_filter = current_user_id if my_tasks else None
        
        # Delegate to service layer for business logic and database query
        # Service handles complex filtering, sorting, and pagination
        result = TaskService.get_all_tasks(
            user_id=user_filter,
            status=status,
            priority=priority,
            category=category,
            assigned_to=assigned_to,
            page=page,
            per_page=per_page
        )
        
        # Return paginated results with metadata
        return jsonify(result), 200
        
    except Exception as e:
        # Handle unexpected errors
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500


# ============================================================================
# GET SINGLE TASK ENDPOINT
# ============================================================================

@api_bp.route('/tasks/<int:task_id>', methods=['GET'])
@jwt_required()
def get_task(task_id):
    """
    Retrieve a specific task by its ID.
    
    Authentication Required: Yes (JWT token)
    
    Path Parameters:
        task_id - Integer ID of the task (from URL)
    
    Example Request:
        GET /api/tasks/42
    
    Success Response (200):
        {
            "task": {
                "id": 42,
                "title": "Complete documentation",
                "description": "Write API docs",
                "status": "in_progress",
                "priority": "medium",
                "category": "Development",
                "due_date": "2024-02-01T17:00:00",
                "assigned_to": 3,
                "assignee": {
                    "id": 3,
                    "username": "developer",
                    "email": "dev@example.com"
                },
                "created_by": 1,
                "creator": {
                    "id": 1,
                    "username": "admin",
                    "email": "admin@example.com"
                },
                "created_at": "2024-01-20T09:00:00",
                "updated_at": "2024-01-21T14:30:00"
            }
        }
    
    Error Responses:
        401 - Missing or invalid JWT token
        404 - Task not found (invalid task_id)
        500 - Server error
    """
    try:
        # Retrieve task from database using service layer
        # Returns Task object or None if not found
        task = TaskService.get_task_by_id(task_id)
        
        # Handle case where task doesn't exist
        if not task:
            return jsonify({
                'error': f'Task with ID {task_id} not found'
            }), 404
        
        # Return task data
        # Note: No permission check here - any authenticated user can view tasks
        # Add permission check here if you want private tasks
        return jsonify({'task': task.to_dict()}), 200
        
    except Exception as e:
        # Handle unexpected errors
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500


# ============================================================================
# UPDATE TASK ENDPOINT
# ============================================================================

@api_bp.route('/tasks/<int:task_id>', methods=['PUT'])
@jwt_required()
def update_task(task_id):
    """
    Update an existing task (partial update supported).
    
    Authentication Required: Yes (JWT token)
    
    Authorization:
        Only the task creator OR the assigned user can update the task
    
    Path Parameters:
        task_id - Integer ID of the task to update
    
    Request Body (JSON):
        Any task fields to update (all optional, send only what needs updating):
        {
            "title": "Updated title",
            "status": "completed",
            "priority": "urgent",
            "assigned_to": 7
        }
    
    Example Request:
        PUT /api/tasks/42
        Body: { "status": "completed" }
    
    Success Response (200):
        {
            "message": "Task updated successfully",
            "task": {
                "id": 42,
                "title": "Complete documentation",
                "status": "completed",  # ← Updated field
                "priority": "medium",
                // ... rest of task data
            }
        }
    
    Error Responses:
        400 - Validation error (invalid field values)
        401 - Missing or invalid JWT token
        403 - Permission denied (not creator or assignee)
        404 - Task not found
        500 - Server error
    """
    try:
        # Get authenticated user ID
        current_user_id = get_jwt_identity()
        
        # Parse update data from request body
        data = request.get_json()
        
        # Validate that request contains data
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Delegate to service layer
        # Service will:
        # 1. Verify task exists
        # 2. Check user has permission to update
        # 3. Validate update data
        # 4. Apply updates to database
        task = TaskService.update_task(task_id, data, user_id=current_user_id)
        
        # Return updated task
        return jsonify({
            'message': 'Task updated successfully',
            'task': task.to_dict()
        }), 200
        
    except ValueError as e:
        # Validation errors or task not found
        return jsonify({'error': str(e)}), 400
    
    except PermissionError as e:
        # User doesn't have permission to update this task
        return jsonify({'error': str(e)}), 403
    
    except Exception as e:
        # Unexpected errors
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500


# ============================================================================
# DELETE TASK ENDPOINT
# ============================================================================

@api_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
@jwt_required()
def delete_task(task_id):
    """
    Permanently delete a task from the system.
    
    Authentication Required: Yes (JWT token)
    
    Authorization:
        ONLY the task creator can delete tasks (not assignees)
    
    Path Parameters:
        task_id - Integer ID of the task to delete
    
    Example Request:
        DELETE /api/tasks/42
    
    Success Response (200):
        {
            "message": "Task 42 deleted successfully"
        }
    
    Error Responses:
        401 - Missing or invalid JWT token
        403 - Permission denied (only creator can delete)
        404 - Task not found
        500 - Server error
    
    Warning:
        This is a HARD DELETE - the task is permanently removed from the database.
        Consider implementing soft delete (is_deleted flag) for production systems
        to allow data recovery and maintain audit trails.
    """
    try:
        # Get authenticated user ID
        current_user_id = get_jwt_identity()
        
        # Delegate to service layer
        # Service will:
        # 1. Verify task exists
        # 2. Check user is the creator (not just assignee)
        # 3. Permanently delete from database
        TaskService.delete_task(task_id, user_id=current_user_id)
        
        # Return success message
        return jsonify({
            'message': f'Task {task_id} deleted successfully'
        }), 200
        
    except ValueError as e:
        # Task not found
        return jsonify({'error': str(e)}), 404
    
    except PermissionError as e:
        # User is not the task creator
        return jsonify({'error': str(e)}), 403
    
    except Exception as e:
        # Unexpected errors (database issues, etc.)
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500


# ============================================================================
# SEARCH TASKS ENDPOINT
# ============================================================================

@api_bp.route('/tasks/search', methods=['GET'])
@jwt_required()
def search_tasks():
    """
    Search for tasks by keyword in title or description.
    
    Authentication Required: Yes (JWT token)
    
    Query Parameters:
        q         - Search query/keyword (required)
        my_tasks  - Limit search to user's tasks (optional, default: false)
    
    Search Behavior:
        - Case-insensitive search
        - Searches both title AND description fields
        - Partial matching (e.g., "doc" matches "documentation")
        - Results ordered by creation date (newest first)
    
    Example Requests:
        GET /api/tasks/search?q=documentation
        GET /api/tasks/search?q=urgent&my_tasks=true
    
    Success Response (200):
        {
            "query": "documentation",    # Echo back the search term
            "count": 3,                  # Number of matching tasks
            "tasks": [
                {
                    "id": 1,
                    "title": "Write API documentation",
                    "description": "Complete docs for REST endpoints",
                    // ... full task object
                },
                {
                    "id": 5,
                    "title": "Review documentation",
                    "description": "QA check all documentation",
                    // ... full task object
                },
                {
                    "id": 12,
                    "title": "Update user guide",
                    "description": "Add documentation for new features",
                    // ... full task object
                }
            ]
        }
    
    Error Responses:
        400 - Missing search query parameter
        401 - Missing or invalid JWT token
        500 - Server error
    """
    try:
        # Extract search query from URL parameters
        # .strip() removes leading/trailing whitespace
        search_term = request.args.get('q', '').strip()
        
        # Validate that search term was provided
        if not search_term:
            return jsonify({
                'error': 'Search query (q) is required'
            }), 400
        
        # Check if limiting search to current user's tasks
        my_tasks = request.args.get('my_tasks', 'false').lower() == 'true'
        
        # Get user ID only if my_tasks=true, otherwise None (search all tasks)
        current_user_id = get_jwt_identity() if my_tasks else None
        
        # Perform search via service layer
        # Service handles database query with ILIKE for case-insensitive matching
        tasks = TaskService.search_tasks(search_term, user_id=current_user_id)
        
        # Return search results with metadata
        return jsonify({
            'query': search_term,           # Echo search term for client reference
            'count': len(tasks),            # Number of results found
            'tasks': [task.to_dict() for task in tasks]  # Full task objects
        }), 200
        
    except Exception as e:
        # Handle unexpected errors
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500