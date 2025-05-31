"""
Main Flask application module for the Basketball Stats Tracker.
Initializes the Flask app, sets up database session handling, and registers routes/blueprints.
"""

from pathlib import Path

from flask import Flask

from app.config import settings
from app.data_access.database_manager import db_manager


def create_app(test_config=None):
    """
    Create and configure the Flask application.

    Args:
        test_config: Configuration dictionary for testing (optional).

    Returns:
        Flask application instance.
    """
    # Create and configure the app
    app = Flask(__name__, template_folder=str(Path(__file__).parent / "web_ui" / "templates"))  # pylint: disable=redefined-outer-name

    # Load configuration
    if test_config is None:
        # Load the instance config when not testing
        app.config.from_mapping(SECRET_KEY=settings.SECRET_KEY, DEBUG=settings.DEBUG)
    else:
        # Load the test config if passed in
        app.config.from_mapping(test_config)

    # Initialize database if needed
    db_manager.get_engine()

    # Database session management for Flask requests
    @app.before_request
    def setup_db_session():
        pass  # Will implement later when routes are added

    @app.teardown_request
    def close_db_session(exception=None):  # pylint: disable=unused-argument
        pass  # Will implement later when routes are added

    # Import and register blueprints
    # from app.web_ui.routes import web_ui_bp
    # app.register_blueprint(web_ui_bp)

    # Simple health check route
    @app.route("/health")
    def health_check():
        from app.config import VERSION_INFO

        return {"status": "ok", "version": VERSION_INFO["version"], "full_version": VERSION_INFO["full_version"]}

    return app


# This will be used by the ASGI server (uvicorn) when running the application
app = create_app()
