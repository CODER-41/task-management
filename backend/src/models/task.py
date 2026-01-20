from datetime import datetime
from backend.src.extensions import db

class Task(db.Model):
    """
    Task Model - Represents a single task in the task management system.
    
    Fields:
        - id: Primary key (auto-generated)
        - title: Task title (required, max 200 chars)
        - description: Detailed task description (optional)
        - status: Current status (pending, in_progress, completed)
        - priority: Task priority (low, medium, high, urgent)
        - category: Task category for organization (optional)
        - due_date: When the task should be completed (optional)
        - assigned_to: User ID of person responsible (optional, foreign key)
        - created_by: User ID of task creator (required, foreign key)
        - created_at: Timestamp of task creation (auto-generated)
        - updated_at: Timestamp of last update (auto-updated)
    """
    # Table name in PostgreSQL database
    __tablename__ = 'tasks'

    #Primary Key
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
     # Core Task Fields
    title = db.Column(
        db.String(200), 
        nullable=False,  # Title is required
        index=True  # Index for faster searching
    )
    
    description = db.Column(
        db.Text,  # Unlimited length text for detailed descriptions
        nullable=True  # Optional field
    )
    
    # Status with predefined values (enum-like behavior)
    # Using db.String with validation in service layer
    status = db.Column(
        db.String(20),
        nullable=False,
        default='pending',  # New tasks default to pending
        index=True  # Index for filtering by status
    )
    
    # Priority level
    priority = db.Column(
        db.String(20),
        nullable=False,
        default='medium',  # Default to medium priority
        index=True  # Index for filtering by priority
    )
    
    # Category for task organization (e.g., "Work", "Personal", "Urgent")
    category = db.Column(
        db.String(50),
        nullable=True,
        index=True  # Index for filtering by category
    )
    
    # Due date - when task should be completed
    due_date = db.Column(
        db.DateTime,
        nullable=True,
        index=True  # Index for sorting/filtering by due date
    )
    
    # Foreign Keys - Relationships with User model
    assigned_to = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='SET NULL'),  # If user deleted, set to NULL
        nullable=True,  # Tasks can be unassigned
        index=True  # Index for filtering by assignee
    )
    
    created_by = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),  # If creator deleted, delete tasks
        nullable=False,  # Every task must have a creator
        index=True
    )
    
    # Timestamp Fields (automatically managed)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow  # Auto-set on creation
    )
    
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,  # Auto-set on creation
        onupdate=datetime.utcnow  # Auto-update on any change
    )
    
    # Relationships - Access related User objects
    assignee = db.relationship(
        'User',
        foreign_keys=[assigned_to],
        backref='assigned_tasks',  # User.assigned_tasks to get all tasks assigned to them
        lazy='joined'  # Eagerly load assignee data to reduce queries
    )
    
    creator = db.relationship(
        'User',
        foreign_keys=[created_by],
        backref='created_tasks',  # User.created_tasks to get all tasks they created
        lazy='joined'
    )
    
    def to_dict(self):
        """
        Convert Task object to dictionary for JSON serialization.
        
        Returns:
            dict: Dictionary representation of the task with all fields
        """
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'category': self.category,
            'due_date': self.due_date.isoformat() if self.due_date else None,  # ISO 8601 format
            'assigned_to': self.assigned_to,
            'assignee': {
                'id': self.assignee.id,
                'username': self.assignee.username,
                'email': self.assignee.email
            } if self.assignee else None,
            'created_by': self.created_by,
            'creator': {
                'id': self.creator.id,
                'username': self.creator.username,
                'email': self.creator.email
            },
            'created_at': self.created_at.isoformat(),  # ISO 8601 format
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        """String representation for debugging"""
        return f'<Task {self.id}: {self.title} ({self.status})>'
 

