"""
Purpose: Business logic for task operations (CRUD)
Depends on: Task model, validators, db
Used by: API routes
Task Service Layer - Contains all business logic for task operations.
Separates business rules from API routes for better testability and reusability.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy import or_, and_
from backend.src.models.task import Task
from backend.src.models.user import User
from backend.src.extensions import db
from backend.src.utils.validators import validate_task_data


class TaskService:
    """Service class for task-related business operations"""
    
    @staticmethod
    def create_task(data: Dict[str, Any], created_by_id: int) -> Task:
        """
        Create a new task with validation.
        
        Args:
            data: Dictionary with task fields (title, description, etc.)
            created_by_id: User ID of task creator
            
        Returns:
            Task: Created task object
            
        Raises:
            ValueError: If validation fails or creator doesn't exist
        """
        # Validate input data
        validated_data = validate_task_data(data, required_fields=['title'])
        
        # Verify creator exists
        creator = User.query.get(created_by_id)
        if not creator:
            raise ValueError(f"User with ID {created_by_id} not found")
        
        # Verify assignee exists (if provided)
        if 'assigned_to' in validated_data and validated_data['assigned_to']:
            assignee = User.query.get(validated_data['assigned_to'])
            if not assignee:
                raise ValueError(f"Assignee with ID {validated_data['assigned_to']} not found")
        
        # Create task object
        task = Task(
            title=validated_data['title'],
            description=validated_data.get('description'),
            status=validated_data.get('status', 'pending'),
            priority=validated_data.get('priority', 'medium'),
            category=validated_data.get('category'),
            due_date=validated_data.get('due_date'),
            assigned_to=validated_data.get('assigned_to'),
            created_by=created_by_id
        )
        
        # Save to database
        db.session.add(task)
        db.session.commit()
        
        return task
    
    @staticmethod
    def get_task_by_id(task_id: int) -> Optional[Task]:
        """
        Retrieve single task by ID.
        
        Args:
            task_id: Task ID to retrieve
            
        Returns:
            Task: Task object if found, None otherwise
        """
        return Task.query.get(task_id)
    
    @staticmethod
    def get_all_tasks(
        user_id: Optional[int] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        category: Optional[str] = None,
        assigned_to: Optional[int] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        Get filtered and paginated list of tasks.
        
        Args:
            user_id: Filter by creator (optional)
            status: Filter by status (optional)
            priority: Filter by priority (optional)
            category: Filter by category (optional)
            assigned_to: Filter by assignee (optional)
            page: Page number (1-indexed)
            per_page: Items per page
            
        Returns:
            dict: Contains 'tasks', 'total', 'page', 'per_page', 'pages'
        """
        # Start with base query
        query = Task.query
        
        # Apply filters
        if user_id:
            # Show tasks created by OR assigned to user
            query = query.filter(
                or_(Task.created_by == user_id, Task.assigned_to == user_id)
            )
        
        if status:
            query = query.filter(Task.status == status)
        
        if priority:
            query = query.filter(Task.priority == priority)
        
        if category:
            query = query.filter(Task.category == category)
        
        if assigned_to:
            query = query.filter(Task.assigned_to == assigned_to)
        
        # Order by due date (nearest first), then by creation date
        query = query.order_by(
            Task.due_date.asc().nullslast(),  # NULL due dates go last
            Task.created_at.desc()
        )
        
        # Paginate results
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False  # Don't raise error if page out of range
        )
        
        return {
            'tasks': [task.to_dict() for task in pagination.items],
            'total': pagination.total,
            'page': pagination.page,
            'per_page': pagination.per_page,
            'pages': pagination.pages
        }
    
    @staticmethod
    def update_task(task_id: int, data: Dict[str, Any], user_id: int) -> Task:
        """
        Update existing task.
        
        Args:
            task_id: ID of task to update
            data: Dictionary with fields to update
            user_id: ID of user making update (for permission check)
            
        Returns:
            Task: Updated task object
            
        Raises:
            ValueError: If task not found or validation fails
            PermissionError: If user doesn't have permission to update
        """
        # Retrieve task
        task = Task.query.get(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} not found")
        
        # Permission check: Only creator or assignee can update
        if task.created_by != user_id and task.assigned_to != user_id:
            raise PermissionError("You don't have permission to update this task")
        
        # Validate update data (fields are optional for updates)
        validated_data = validate_task_data(data)
        
        # Verify assignee exists if being changed
        if 'assigned_to' in validated_data and validated_data['assigned_to']:
            assignee = User.query.get(validated_data['assigned_to'])
            if not assignee:
                raise ValueError(f"Assignee with ID {validated_data['assigned_to']} not found")
        
        # Update fields
        for field, value in validated_data.items():
            if hasattr(task, field):
                setattr(task, field, value)
        
        # Save changes
        db.session.commit()
        
        return task
    
    @staticmethod
    def delete_task(task_id: int, user_id: int) -> bool:
        """
        Delete a task (soft or hard delete).
        
        Args:
            task_id: ID of task to delete
            user_id: ID of user requesting deletion
            
        Returns:
            bool: True if deleted successfully
            
        Raises:
            ValueError: If task not found
            PermissionError: If user doesn't have permission
        """
        # Retrieve task
        task = Task.query.get(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} not found")
        
        # Permission check: Only creator can delete
        if task.created_by != user_id:
            raise PermissionError("Only the task creator can delete this task")
        
        # Hard delete (for now - could implement soft delete with is_deleted flag)
        db.session.delete(task)
        db.session.commit()
        
        return True
    
    @staticmethod
    def search_tasks(search_term: str, user_id: Optional[int] = None) -> List[Task]:
        """
        Search tasks by title or description.
        
        Args:
            search_term: Text to search for
            user_id: Limit search to user's tasks (optional)
            
        Returns:
            list: List of matching Task objects
        """
        # Build search query (case-insensitive)
        search_pattern = f"%{search_term}%"
        query = Task.query.filter(
            or_(
                Task.title.ilike(search_pattern),
                Task.description.ilike(search_pattern)
            )
        )
        
        # Filter by user if specified
        if user_id:
            query = query.filter(
                or_(Task.created_by == user_id, Task.assigned_to == user_id)
            )
        
        return query.order_by(Task.created_at.desc()).all()