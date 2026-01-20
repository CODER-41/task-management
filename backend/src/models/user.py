"""
Purpose: User model for authentication and task assignment.
Depends on: SQLALchemy, werkzeug.security
Used by: Auth API, Task management API
"""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from backend.src.extensions import db


class User(db.Model):
    """
    User Model - Represents system users who can create and be assigned tasks.
    
    Fields:
        - id: Primary key
        - username: Unique username for login
        - email: Unique email address
        - password_hash: Bcrypt hashed password (never store plain passwords)
        - first_name: User's first name
        - last_name: User's last name
        - is_active: Whether account is active
        - created_at: Account creation timestamp
        - updated_at: Last update timestamp
    """
    
    __tablename__ = 'users'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Authentication Fields
    username = db.Column(
        db.String(80),
        unique=True,  # No duplicate usernames
        nullable=False,
        index=True  # Fast username lookups for login
    )
    
    email = db.Column(
        db.String(120),
        unique=True,  # No duplicate emails
        nullable=False,
        index=True  # Fast email lookups
    )
    
    # Password stored as hash (NEVER store plaintext passwords)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Profile Fields
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    
    # Account Status
    is_active = db.Column(
        db.Boolean,
        default=True,  # Accounts active by default
        nullable=False
    )
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_password(self, password):
        """
        Hash and store password securely using bcrypt.
        
        Args:
            password (str): Plain text password from user input
        """
        # generate_password_hash uses bcrypt with salt
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """
        Verify password against stored hash.
        
        Args:
            password (str): Plain text password to verify
            
        Returns:
            bool: True if password matches, False otherwise
        """
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self, include_email=False):
        """
        Convert User to dictionary (exclude sensitive data by default).
        
        Args:
            include_email (bool): Whether to include email in response
            
        Returns:
            dict: Safe user data for API responses
        """
        data = {
            'id': self.id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat()
        }
        
        # Only include email if explicitly requested (e.g., for own profile)
        if include_email:
            data['email'] = self.email
            
        return data
    
    def __repr__(self):
        """String representation for debugging"""
        return f'<User {self.id}: {self.username}>'