"""
Integration test configuration and shared fixtures.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def reset_app_state():
    """
    Automatically reset FastAPI app state before and after each test.
    This prevents tests from interfering with each other when run together.
    """
    from app.web_ui.api import app

    # Store original state
    original_overrides = app.dependency_overrides.copy()

    # Clear any existing overrides before test
    app.dependency_overrides.clear()

    yield

    # Restore original state after test
    app.dependency_overrides.clear()
    app.dependency_overrides.update(original_overrides)


@pytest.fixture
def isolated_client(test_db_file_session):
    """
    Create a FastAPI test client with proper isolation.
    This ensures each test gets a clean app state.
    """
    from app.auth.dependencies import get_current_user
    from app.auth.models import User
    from app.web_ui.api import app
    from app.web_ui.dependencies import get_db

    # Create fresh overrides for this test
    def override_get_db():
        return test_db_file_session

    def mock_current_user():
        return User(id=1, username="testuser", email="test@example.com", role="admin", is_active=True)

    # Store current overrides
    original_overrides = app.dependency_overrides.copy()

    try:
        # Clear and set new overrides
        app.dependency_overrides.clear()
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = mock_current_user

        # Create client
        with TestClient(app) as client:
            yield client
    finally:
        # Always restore original state
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)


@pytest.fixture
def isolated_unauthenticated_client(test_db_file_session):
    """
    Create an unauthenticated FastAPI test client with proper isolation.
    """
    from app.web_ui.api import app
    from app.web_ui.dependencies import get_db

    # Create fresh overrides for this test
    def override_get_db():
        return test_db_file_session

    # Store current overrides
    original_overrides = app.dependency_overrides.copy()

    try:
        # Clear and set new overrides
        app.dependency_overrides.clear()
        app.dependency_overrides[get_db] = override_get_db

        # Create client
        with TestClient(app) as client:
            yield client
    finally:
        # Always restore original state
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)
