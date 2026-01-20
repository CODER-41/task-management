import os
from datetime import timedelta

class Config:
    """
    Base configuration class for the Flask application.
    Contains all-environment-specific settings and security configurations.
    """

    # Security : Secret Key for session management and JWT tokens
    # NEVER hardcode secret keys in production code.
    SECRET_KEY = os.getenv('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://postgres:postgres@localhost:5432/taskmanager_db'


    # Disable SQLAlchemy event system to save resources
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT Configuration for authentication
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)  # Token expires after 1 hour
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)  # Refresh token expires after 30 days
    
    # API Rate Limiting (requests per minute)
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL') or 'memory://'
    
    # CORS Configuration (Cross-Origin Resource Sharing)
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000').split(',')
    
    # Pagination defaults
    ITEMS_PER_PAGE = 20
    MAX_ITEMS_PER_PAGE = 100


class DevelopmentConfig(Config):
    """Development-specific configuration"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production-specific configuration with enhanced security"""
    DEBUG = False
    TESTING = False
    
    # Force HTTPS in production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


class TestingConfig(Config):
    """Testing configuration with separate test database"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:postgres@localhost:5432/taskmanager_test_db'
    WTF_CSRF_ENABLED = False


# Configuration dictionary for easy access
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
