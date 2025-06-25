"""
Integration test configuration and shared fixtures.
"""

import pytest


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
def isolated_client(authenticated_client):
    """
    DEPRECATED: Use authenticated_client from main conftest.py instead.
    This fixture is kept for backward compatibility but should be removed.
    """
    return authenticated_client


@pytest.fixture
def isolated_unauthenticated_client(unauthenticated_client):
    """
    DEPRECATED: Use unauthenticated_client from main conftest.py instead.
    This fixture is kept for backward compatibility but should be removed.
    """
    return unauthenticated_client
