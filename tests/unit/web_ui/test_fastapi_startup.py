"""
Unit tests for FastAPI application startup and configuration.

Tests that the FastAPI app can start successfully without database issues,
side effects, or blocking operations that would cause Cloud Run deployment failures.
"""

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


def test_fastapi_app_imports_successfully():
    """Test that the FastAPI app can be imported without side effects."""
    try:
        from app.web_ui.api import app
        assert app is not None
        assert app.title == "Basketball Stats Tracker"
    except Exception as e:
        pytest.fail(f"FastAPI app failed to import: {e}")


def test_fastapi_app_starts_without_database():
    """Test that FastAPI app can start even if database is unavailable."""
    # Mock the database connection to fail
    with patch('app.data_access.database_manager.create_engine') as mock_create_engine:
        mock_create_engine.side_effect = Exception("Database unavailable")
        
        try:
            from app.web_ui.api import app
            client = TestClient(app)
            
            # The app should still be created even if database is down
            assert app is not None
            
            # Routes should be registered
            routes = [route.path for route in app.routes]
            assert len(routes) > 0
            
        except Exception as e:
            pytest.fail(f"FastAPI app failed to start without database: {e}")


def test_fastapi_app_no_automatic_migrations():
    """Test that importing the FastAPI app doesn't trigger database migrations."""
    migration_called = False
    
    def mock_migration(*args, **kwargs):
        nonlocal migration_called
        migration_called = True
        
    with patch('app.services.database_admin_service.DatabaseAdminService.initialize_schema', side_effect=mock_migration):
        with patch('app.services.database_admin_service.DatabaseAdminService.upgrade_to_head', side_effect=mock_migration):
            try:
                from app.web_ui.api import app
                client = TestClient(app)
                
                # Verify no migrations were triggered during app creation
                assert not migration_called, "App startup should not trigger database migrations"
                
            except Exception as e:
                pytest.fail(f"FastAPI app startup triggered database operations: {e}")


def test_production_environment_variables():
    """Test that the app starts correctly with production environment variables."""
    prod_env = {
        "ENVIRONMENT": "production",
        "SECRET_KEY": "test-secret-key-for-production",
        "DATABASE_URL": "postgresql://user:pass@localhost:5432/testdb"
    }
    
    with patch.dict(os.environ, prod_env, clear=False):
        try:
            from app.web_ui.api import app
            client = TestClient(app)
            
            # App should start successfully in production mode
            assert app is not None
            
            # Verify middleware is configured for production
            middleware_types = [type(middleware).__name__ for middleware in app.user_middleware]
            assert "TrustedHostMiddleware" in middleware_types
            
        except Exception as e:
            pytest.fail(f"FastAPI app failed to start in production mode: {e}")


def test_health_endpoint_responds():
    """Test that the health endpoint is accessible during startup."""
    try:
        from app.web_ui.api import app
        client = TestClient(app)
        
        # Health endpoint should be available and respond quickly
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"
        assert "version" in data
        
    except Exception as e:
        pytest.fail(f"Health endpoint failed during startup: {e}")


def test_app_startup_time():
    """Test that app startup completes within reasonable time limits."""
    import time
    
    start_time = time.time()
    
    try:
        from app.web_ui.api import app
        client = TestClient(app)
        
        startup_time = time.time() - start_time
        
        # App should start within 5 seconds (Cloud Run timeout is much longer)
        assert startup_time < 5.0, f"App startup took {startup_time:.2f}s, too slow for Cloud Run"
        
    except Exception as e:
        pytest.fail(f"App startup test failed: {e}")


def test_no_blocking_database_operations_at_startup():
    """Test that no blocking database operations occur during app import."""
    database_operations = []
    
    def track_db_operation(operation_name):
        def wrapper(*args, **kwargs):
            database_operations.append(operation_name)
            # Don't actually execute the operation
            return None
        return wrapper
    
    with patch('app.data_access.database_manager.create_engine', side_effect=track_db_operation('create_engine')):
        with patch('sqlalchemy.orm.sessionmaker', side_effect=track_db_operation('sessionmaker')):
            try:
                from app.web_ui.api import app
                
                # Some database setup is expected, but no blocking operations
                allowed_operations = ['create_engine']  # Engine creation is lazy and OK
                blocking_operations = [op for op in database_operations if op not in allowed_operations]
                
                assert len(blocking_operations) == 0, f"Blocking database operations detected: {blocking_operations}"
                
            except Exception as e:
                pytest.fail(f"Database operation test failed: {e}")