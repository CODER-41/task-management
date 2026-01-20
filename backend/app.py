"""
Flask Application Factory Module

This module implements the Application Factory pattern, which provides several benefits:

1. **Multiple Instances**: Create different app instances with different configurations
   - Development app with debug mode and SQLite
   - Production app with PostgreSQL and security hardening
   - Testing app with test database and no CSRF

2. **Testing**: Easy to create isolated app instances for each test
3. **Configuration**: Load different configs based on environment
4. **Extension Initialization**: Properly initialize extensions with app context

Factory Pattern Flow:
    create_app() → Load Config → Initialize Extensions → Register Blueprints → Return App

Usage:
    # Development
    app = create_app('development')
    app.run(debug=True)
    
    # Production (with Gunicorn)
    gunicorn -w 4 -b 0.0.0.0:5000 "backend.app:create_app('production')"
    
    # Testing
    app = create_app('testing')
    test_client = app.test_client()
"""

import os
from flask import Flask, jsonify
from backend.config import config
from backend.src.extensions import db, jwt, cors
from backend.src.api import api_bp


def create_app(config_name=None):
    """
    Application Factory - Creates and configures a Flask application instance.
    
    This function follows the factory pattern to create a Flask app with the
    appropriate configuration for the target environment.
    
    Args:
        config_name (str, optional): Name of configuration to use.
            Valid values: 'development', 'production', 'testing'
            If None, reads from FLASK_ENV environment variable
            Defaults to 'development' if FLASK_ENV not set
    
    Returns:
        Flask: Fully configured Flask application instance ready to run
    
    Configuration Precedence:
        1. Explicit config_name parameter (highest priority)
        2. FLASK_ENV environment variable
        3. Default to 'development' (lowest priority)
    
    Example:
        # Explicit configuration
        app = create_app('production')
        
        # From environment variable
        os.environ['FLASK_ENV'] = 'testing'
        app = create_app()  # Uses 'testing' config
        
        # Default
        app = create_app()  # Uses 'development' config
    """
    
    # ========================================================================
    # STEP 1: Create Flask Application Instance
    # ========================================================================
    
    # __name__ helps Flask locate templates, static files, etc.
    app = Flask(__name__)
    
    
    # ========================================================================
    # STEP 2: Load Configuration
    # ========================================================================
    
    # Determine which configuration to use
    if config_name is None:
        # Try to get from environment variable, default to 'development'
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    # Load configuration from config.py
    # config[config_name] returns the appropriate Config class
    # from_object() loads all UPPERCASE attributes from the class
    app.config.from_object(config[config_name])
    
    # Optional: Log which configuration is being used (helpful for debugging)
    print(f"Starting application with '{config_name}' configuration")
    
    
    # ========================================================================
    # STEP 3: Initialize Flask Extensions
    # ========================================================================
    
    # Initialize SQLAlchemy (Database ORM)
    # Creates db.session for database operations and db.Model base class
    db.init_app(app)
    
    # Initialize JWT Manager (Authentication)
    # Enables @jwt_required() decorator and token creation/validation
    jwt.init_app(app)
    
    # Initialize CORS (Cross-Origin Resource Sharing)
    # Allows frontend (React) running on different port to access API
    cors.init_app(app, resources={
        r"/api/*": {  # Apply CORS only to /api/* routes
            "origins": app.config['CORS_ORIGINS'],  # Allowed origins from config
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Allowed HTTP methods
            "allow_headers": ["Content-Type", "Authorization"],  # Allowed headers
            "expose_headers": ["Content-Type", "Authorization"],  # Headers client can access
            "supports_credentials": True  # Allow cookies/auth headers
        }
    })
    
    
    # ========================================================================
    # STEP 4: Register Blueprints (Route Modules)
    # ========================================================================
    
    # Register API blueprint (contains all /api/tasks routes)
    # Blueprint prefix is /api, so routes become /api/tasks, /api/tasks/<id>, etc.
    app.register_blueprint(api_bp)
    
    # TODO: Register additional blueprints as they're created
    # from backend.src.api import auth_bp
    # app.register_blueprint(auth_bp)
    
    
    # ========================================================================
    # STEP 5: Database Initialization
    # ========================================================================
    
    # Create database tables if they don't exist
    # Only in development - production should use migrations (Alembic/Flask-Migrate)
    with app.app_context():
        if config_name == 'development':
            # db.create_all() creates tables based on model definitions
            # Safe to call multiple times (won't recreate existing tables)
            db.create_all()
            print("Database tables created/verified")
        
        # In production, this should be handled by migrations:
        # flask db init
        # flask db migrate -m "Initial migration"
        # flask db upgrade
    
    
    # ========================================================================
    # STEP 6: Register Application Routes (Non-Blueprint Routes)
    # ========================================================================
    
    @app.route('/health')
    def health_check():
        """
        Health Check Endpoint
        
        Used by:
        - Load balancers to check if instance is healthy
        - Monitoring systems (Prometheus, Datadog, etc.)
        - Deployment scripts to verify successful deployment
        - Container orchestration (Kubernetes liveness/readiness probes)
        
        Returns:
            JSON response with status and environment
            Always returns 200 if app is running
        
        Example Response:
            {
                "status": "healthy",
                "environment": "production"
            }
        """
        return jsonify({
            'status': 'healthy',
            'environment': config_name
        }), 200
    
    
    @app.route('/')
    def index():
        """
        Root Endpoint - API Information
        
        Provides basic information about the API and available endpoints.
        Useful for developers discovering the API or verifying deployment.
        
        Returns:
            JSON with API metadata and endpoint directory
        
        Example Response:
            {
                "message": "Task Management API",
                "version": "1.0.0",
                "endpoints": {
                    "health": "/health",
                    "api": "/api",
                    "tasks": "/api/tasks"
                }
            }
        """
        return jsonify({
            'message': 'Task Management API',
            'version': '1.0.0',
            'endpoints': {
                'health': '/health',
                'api': '/api',
                'tasks': '/api/tasks',
                'docs': '/api/docs'  # TODO: Add when API documentation is implemented
            }
        }), 200
    
    
    # ========================================================================
    # STEP 7: Register Global Error Handlers
    # ========================================================================
    
    @app.errorhandler(404)
    def not_found(error):
        """
        Handle 404 Not Found Errors
        
        Triggered when:
        - User requests a route that doesn't exist
        - Resource ID doesn't exist (handled in routes, but this is fallback)
        
        Args:
            error: Flask error object (unused but required by Flask)
        
        Returns:
            JSON error response with 404 status
        """
        return jsonify({
            'error': 'Resource not found',
            'message': 'The requested URL was not found on the server'
        }), 404
    
    
    @app.errorhandler(500)
    def internal_error(error):
        """
        Handle 500 Internal Server Errors
        
        Triggered when:
        - Unhandled exception occurs in route handler
        - Database errors that aren't caught
        - Any unexpected application error
        
        Important: Rollback database session to prevent partial commits
        
        Args:
            error: Flask error object (contains exception details)
        
        Returns:
            JSON error response with 500 status
        
        Production Note:
            In production, log error details to monitoring system
            but don't expose internal error details to client
        """
        # Rollback any failed database transactions
        # Prevents partial/corrupt data from being committed
        db.session.rollback()
        
        # In production, log error to monitoring system
        # import logging
        # logging.error(f'Internal Server Error: {error}')
        
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred. Please try again later.'
            # In development, you might add: 'details': str(error)
        }), 500
    
    
    @app.errorhandler(400)
    def bad_request(error):
        """
        Handle 400 Bad Request Errors
        
        Triggered when:
        - Request JSON is malformed
        - Required parameters are missing
        - Request format is invalid
        
        Args:
            error: Flask error object
        
        Returns:
            JSON error response with 400 status
        """
        return jsonify({
            'error': 'Bad request',
            'message': 'The request could not be understood or was missing required parameters'
        }), 400
    
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        """
        Handle 405 Method Not Allowed Errors
        
        Triggered when:
        - Client uses wrong HTTP method (e.g., POST to a GET-only endpoint)
        
        Args:
            error: Flask error object
        
        Returns:
            JSON error response with 405 status
        """
        return jsonify({
            'error': 'Method not allowed',
            'message': 'The HTTP method is not allowed for this endpoint'
        }), 405
    
    
    # ========================================================================
    # STEP 8: Register JWT Error Handlers
    # ========================================================================
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        """
        Handle expired JWT tokens
        
        Triggered when user's JWT access token has expired
        Client should request a new token using refresh token
        
        Args:
            jwt_header: JWT header containing token metadata
            jwt_payload: JWT payload containing user claims and expiration
        
        Returns:
            JSON error response with 401 status
        """
        return jsonify({
            'error': 'Token expired',
            'message': 'The authentication token has expired. Please login again.'
        }), 401
    
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        """
        Handle invalid JWT tokens
        
        Triggered when:
        - Token signature is invalid (tampered with)
        - Token format is malformed
        - Token algorithm doesn't match expected
        - Token is corrupted
        
        Args:
            error: Error message describing why token is invalid
        
        Returns:
            JSON error response with 401 status
        """
        return jsonify({
            'error': 'Invalid token',
            'message': 'The authentication token is invalid. Please login again.'
        }), 401
    
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        """
        Handle missing JWT tokens
        
        Triggered when:
        - No Authorization header is provided
        - Authorization header doesn't start with 'Bearer '
        - Endpoint requires JWT but none provided
        - Token is empty or whitespace only
        
        Args:
            error: Error message describing the authorization issue
        
        Returns:
            JSON error response with 401 status
        """
        return jsonify({
            'error': 'Authorization required',
            'message': 'Request does not contain a valid authentication token. Please login.'
        }), 401
    
    
    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        """
        Handle revoked JWT tokens
        
        Triggered when:
        - Token has been explicitly revoked (user logout, password change, etc.)
        - Token is in revocation list/blacklist
        
        Note: Requires token revocation implementation (Redis/database)
        To use this, implement a token blocklist with Flask-JWT-Extended
        
        Args:
            jwt_header: JWT header data
            jwt_payload: JWT payload data (contains user_id, expiration, etc.)
        
        Returns:
            JSON error response with 401 status
        """
        return jsonify({
            'error': 'Token revoked',
            'message': 'The authentication token has been revoked. Please login again.'
        }), 401
    
    
    @jwt.needs_fresh_token_loader
    def token_not_fresh_callback(jwt_header, jwt_payload):
        """
        Handle non-fresh tokens for sensitive operations
        
        Triggered when:
        - Operation requires fresh token (recent login)
        - User is using a token obtained via refresh (not original login)
        - Sensitive operations require re-authentication
        
        Fresh tokens are issued on direct login
        Non-fresh tokens are issued via refresh endpoint
        
        Use @jwt_required(fresh=True) for sensitive operations like:
        - Changing password
        - Updating email
        - Deleting account
        - Making payments
        
        Args:
            jwt_header: JWT header data
            jwt_payload: JWT payload data
        
        Returns:
            JSON error response with 401 status
        """
        return jsonify({
            'error': 'Fresh token required',
            'message': 'This operation requires a fresh authentication token. Please login again.'
        }), 401
    
    
    # ========================================================================
    # STEP 9: Register Request/Response Hooks
    # ========================================================================
    
    @app.before_request
    def before_request_func():
        """
        Execute before each request is processed
        
        This runs BEFORE the route handler is called
        Useful for:
        - Request logging and monitoring
        - Rate limiting checks
        - Authentication preprocessing
        - Request ID generation for tracing
        - Database connection setup
        
        Note: This runs for EVERY request, so keep it lightweight
        Avoid heavy computations or blocking operations here
        """
        # Example: Log all incoming requests in development mode
        if app.config.get('DEBUG'):
            from flask import request
            print(f"{request.method} {request.path}")
    
    
    @app.after_request
    def after_request_func(response):
        """
        Execute after each request (before sending response to client)
        
        This runs AFTER the route handler completes successfully
        Useful for:
        - Adding security headers
        - Response logging
        - Response time tracking
        - Cache control headers
        - CORS headers (handled by flask-cors, but can customize here)
        
        Args:
            response: Flask Response object that will be sent to client
        
        Returns:
            Modified Response object with additional headers
        """
        # Add security headers to all responses
        
        # Prevents MIME type sniffing attacks
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # Prevents clickjacking by disallowing iframe embedding
        response.headers['X-Frame-Options'] = 'DENY'
        
        # XSS protection (deprecated but still useful for older browsers)
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Content Security Policy (basic, customize as needed)
        # response.headers['Content-Security-Policy'] = "default-src 'self'"
        
        # Add HSTS header in production (forces HTTPS for 1 year)
        if app.config.get('ENV') == 'production':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        return response
    
    
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        """
        Clean up resources after request or when app context is torn down
        
        Automatically called at:
        - End of each request
        - When app context is popped/destroyed
        - On application shutdown
        
        Ensures proper cleanup of:
        - Database connections
        - File handles
        - Network connections
        
        Args:
            exception: Exception that caused teardown (None if normal completion)
                      Can be used for error logging/cleanup
        """
        # SQLAlchemy handles session cleanup automatically
        # But explicit removal doesn't hurt and ensures proper cleanup
        db.session.remove()
        
        # If there was an exception, you might want to log it
        # if exception:
        #     import logging
        #     logging.error(f'Request teardown with exception: {exception}')
    
    
    # ========================================================================
    # STEP 10: Register CLI Commands (Flask Command Line Interface)
    # ========================================================================
    
    @app.cli.command('init-db')
    def init_db_command():
        """
        Initialize the database (create all tables)
        
        Usage:
            flask init-db
        
        This command creates all database tables based on model definitions.
        Safe to run multiple times (won't recreate existing tables).
        Useful for:
        - Initial database setup
        - Creating tables after model changes (use migrations in production)
        - Resetting test database
        
        In production, use Flask-Migrate instead:
            flask db init
            flask db migrate -m "Initial migration"
            flask db upgrade
        """
        with app.app_context():
            # Create all tables defined in models
            db.create_all()
            print('Database initialized successfully')
            print('   All tables created based on model definitions')
    
    
    @app.cli.command('seed-db')
    def seed_db_command():
        """
        Seed database with sample data (development/testing only)
        
        Usage:
            flask seed-db
        
        Creates sample users and tasks for development and testing.
        Checks if data already exists to prevent duplicates.
        
        Sample Data Created:
        - 2 users (admin, regular user)
        - 2 sample tasks
        
        WARNING: Only use in development/testing environments
        """
        from backend.src.models.user import User
        from backend.src.models.task import Task
        
        with app.app_context():
            # Check if data already exists to prevent duplicates
            if User.query.first():
                print('Database already contains data. Skipping seed.')
                print('   Use "flask reset-db" to clear database first')
                return
            
            # ================================================================
            # Create Sample Users
            # ================================================================
            
            # Admin user
            admin = User(
                username='admin',
                email='admin@example.com',
                first_name='Admin',
                last_name='User'
            )
            admin.set_password('admin123')  # Password is hashed automatically
            
            # Regular user
            user1 = User(
                username='johndoe',
                email='john@example.com',
                first_name='John',
                last_name='Doe'
            )
            user1.set_password('password123')
            
            # Add users to session and commit
            db.session.add(admin)
            db.session.add(user1)
            db.session.commit()
            
            print(f'Created {User.query.count()} users:')
            print(f'   - admin (admin@example.com) - password: admin123')
            print(f'   - johndoe (john@example.com) - password: password123')
            
            # ================================================================
            # Create Sample Tasks
            # ================================================================
            
            task1 = Task(
                title='Complete project documentation',
                description='Write comprehensive API documentation for all endpoints',
                status='in_progress',
                priority='high',
                category='Development',
                created_by=admin.id,
                assigned_to=user1.id
            )
            
            task2 = Task(
                title='Review pull requests',
                description='Review and merge pending PRs from team members',
                status='pending',
                priority='medium',
                category='Development',
                created_by=admin.id
            )
            
            task3 = Task(
                title='Update dependencies',
                description='Update all Python packages to latest stable versions',
                status='pending',
                priority='low',
                category='Maintenance',
                created_by=user1.id
            )
            
            # Add tasks to session and commit
            db.session.add(task1)
            db.session.add(task2)
            db.session.add(task3)
            db.session.commit()
            
            print(f'Created {Task.query.count()} sample tasks')
            print(' Database seeding complete!')
            print('You can now login with:')
            print('  Username: admin, Password: admin123')
            print('  Username: johndoe, Password: password123')
    
    
    @app.cli.command('reset-db')
    def reset_db_command():
        """
        Reset database (drop all tables and recreate)
        
        Usage:
            flask reset-db
        
        WARNING: This PERMANENTLY DELETES ALL DATA
        Use only in development/testing environments
        
        Steps:
        1. Drops all existing tables
        2. Recreates tables from model definitions
        3. Database is empty after this command
        
        Follow with:
            flask seed-db (to add sample data)
        """
        with app.app_context():
            # Prompt for confirmation (safety check)
            print('WARNING: This will DELETE ALL DATA in the database!')
            print(f'   Database: {app.config["SQLALCHEMY_DATABASE_URI"]}')
            confirm = input('   Type "yes" to confirm: ')

            if confirm.lower() != 'yes':
                print('Reset cancelled')
                return
            
            # Drop all tables
            db.drop_all()
            print('All tables dropped')

            # Recreate all tables
            db.create_all()
            print('All tables recreated')
            print('Database reset complete! Use "flask seed-db" to add sample data.')
    
    
    # ========================================================================
    # STEP 11: Return Configured Application
    # ========================================================================
    
    print("Application factory complete - app ready to run")
    return app


# ============================================================================
# Development Server Entry Point
# ============================================================================

if __name__ == '__main__':
    """
    Run development server directly with: python app.py
    
    This block only executes when running the file directly (not when imported).
    Used for local development and testing.
    
    Development Server Features:
    - Auto-reload on code changes (use_reloader=True)
    - Debug mode with interactive debugger
    - Detailed error pages with stack traces
    - Werkzeug debugger console
    
    NOT suitable for production - use gunicorn/uwsgi instead:
        
        Production deployment examples:
        
        # Basic gunicorn (4 workers)
        gunicorn -w 4 -b 0.0.0.0:5000 "backend.app:create_app('production')"
        
        # With environment variable
        FLASK_ENV=production gunicorn -w 4 -b 0.0.0.0:5000 "backend.app:create_app()"
        
        # With more options (timeout, logging, worker class)
        gunicorn -w 4 -b 0.0.0.0:5000 \
            --timeout 120 \
            --access-logfile - \
            --error-logfile - \
            --worker-class=gthread \
            --threads=2 \
            "backend.app:create_app('production')"
        
        # Using uwsgi
        uwsgi --http :5000 --wsgi-file backend/app.py --callable app
    """
    
    # Create app with development configuration
    app = create_app('development')
    
    # Run development server
    app.run(
        host='0.0.0.0',      # Listen on all network interfaces
                             # 0.0.0.0 allows external access (useful for testing on mobile)
                             # Use 127.0.0.1 to restrict to localhost only
        
        port=5000,           # Default Flask port
                             # Change if port 5000 is already in use
        
        debug=True,          # Enable debug mode
                             # - Detailed error pages with interactive debugger
                             # - Auto-reload on code changes
                             # - WARNING: Never use in production (security risk)
        
        use_reloader=True,   # Auto-reload when code changes
                             # Watches Python files and restarts server on changes
                             # Set to False if causing issues with debuggers
        
        threaded=True        # Handle multiple requests concurrently
                             # Each request runs in a separate thread
                             # Better performance for development testing
    )
