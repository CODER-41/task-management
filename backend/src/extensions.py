"""
Flask Extensions Initialization.
Extensions are initialized here and bound to the app in app.py.
This pattern allows extensions to be imported by models before app creation.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS

# Initialize SQLAlchemy (database ORM)
# Will be bound to Flask app with db.init_app(app)
db = SQLAlchemy()

# Initialize JWT Manager (for authentication tokens)
jwt = JWTManager()

# Initialize CORS (Cross-Origin Resource Sharing for frontend)
cors = CORS()