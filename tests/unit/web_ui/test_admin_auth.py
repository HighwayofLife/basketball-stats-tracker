"""
Unit tests for admin authentication requirements.
"""

import pytest
from fastapi.testclient import TestClient

from app.data_access.models import Base
from app.web_ui.api import app
from app.web_ui.dependencies import get_db


class TestAdminAuthentication:
    """Test cases for admin authentication requirements."""

    @pytest.fixture
    def test_db_file(self, tmp_path):
        """Create a temporary database file for testing."""
        db_file = tmp_path / "test.db"
        return str(db_file)

    @pytest.fixture
    def test_db_engine(self, test_db_file):
        """Create a database engine with a file-based database."""
        from sqlalchemy import create_engine

        engine = create_engine(f"sqlite:///{test_db_file}")
        Base.metadata.create_all(engine)
        yield engine
        Base.metadata.drop_all(engine)

    @pytest.fixture
    def db_session(self, test_db_engine):
        """Override the db_session fixture to use our test engine."""
        from sqlalchemy.orm import sessionmaker

        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    @pytest.fixture
    def admin_client(self, db_session, test_db_engine, monkeypatch):
        """Create a test client with admin user authentication."""
        from contextlib import contextmanager

        from sqlalchemy.orm import Session

        db_session.commit()

        @contextmanager
        def test_get_db_session():
            new_session = Session(bind=test_db_engine)
            try:
                yield new_session
            finally:
                new_session.close()

        # Monkey-patch database sessions
        import app.data_access.db_session as db_session_module
        import app.web_ui.routers.admin as admin_module

        monkeypatch.setattr(db_session_module, "get_db_session", test_get_db_session)
        monkeypatch.setattr(admin_module, "get_db_session", test_get_db_session)

        def override_get_db():
            new_session = Session(bind=test_db_engine)
            try:
                yield new_session
            finally:
                new_session.close()

        # Mock admin user authentication
        from app.auth.dependencies import get_current_user, require_admin
        from app.auth.models import User, UserRole

        def mock_admin_user():
            """Mock admin user for testing."""
            return User(
                id=1,
                username="admin",
                email="admin@example.com",
                role=UserRole.ADMIN,
                is_active=True,
                provider="local",
            )

        original_overrides = app.dependency_overrides.copy()
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = mock_admin_user
        app.dependency_overrides[require_admin] = mock_admin_user

        try:
            with TestClient(app) as client:
                yield client
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(original_overrides)

    @pytest.fixture
    def non_admin_client(self, db_session, test_db_engine, monkeypatch):
        """Create a test client with non-admin user authentication."""
        from contextlib import contextmanager

        from sqlalchemy.orm import Session

        db_session.commit()

        @contextmanager
        def test_get_db_session():
            new_session = Session(bind=test_db_engine)
            try:
                yield new_session
            finally:
                new_session.close()

        # Monkey-patch database sessions
        import app.data_access.db_session as db_session_module
        import app.web_ui.routers.admin as admin_module

        monkeypatch.setattr(db_session_module, "get_db_session", test_get_db_session)
        monkeypatch.setattr(admin_module, "get_db_session", test_get_db_session)

        def override_get_db():
            new_session = Session(bind=test_db_engine)
            try:
                yield new_session
            finally:
                new_session.close()

        # Mock non-admin user authentication
        from fastapi import HTTPException, status

        from app.auth.dependencies import get_current_user, require_admin
        from app.auth.models import User, UserRole

        def mock_regular_user():
            """Mock regular user for testing."""
            return User(
                id=2,
                username="regular",
                email="regular@example.com",
                role=UserRole.USER,
                is_active=True,
                provider="local",
            )

        def mock_require_admin():
            """Mock require_admin that fails for non-admin users."""
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

        original_overrides = app.dependency_overrides.copy()
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = mock_regular_user
        app.dependency_overrides[require_admin] = mock_require_admin

        try:
            with TestClient(app) as client:
                yield client
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(original_overrides)

    @pytest.fixture
    def unauthenticated_client(self, db_session, test_db_engine, monkeypatch):
        """Create a test client with no authentication."""
        from contextlib import contextmanager

        from sqlalchemy.orm import Session

        db_session.commit()

        @contextmanager
        def test_get_db_session():
            new_session = Session(bind=test_db_engine)
            try:
                yield new_session
            finally:
                new_session.close()

        # Monkey-patch database sessions
        import app.data_access.db_session as db_session_module
        import app.web_ui.routers.admin as admin_module

        monkeypatch.setattr(db_session_module, "get_db_session", test_get_db_session)
        monkeypatch.setattr(admin_module, "get_db_session", test_get_db_session)

        def override_get_db():
            new_session = Session(bind=test_db_engine)
            try:
                yield new_session
            finally:
                new_session.close()

        # Mock unauthenticated state
        from fastapi import HTTPException, status

        from app.auth.dependencies import get_current_user, require_admin

        def mock_unauthenticated():
            """Mock unauthenticated state."""
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

        original_overrides = app.dependency_overrides.copy()
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = mock_unauthenticated
        app.dependency_overrides[require_admin] = mock_unauthenticated

        try:
            with TestClient(app) as client:
                yield client
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(original_overrides)

    def test_admin_can_access_seasons(self, admin_client):
        """Test that admin users can access seasons endpoints."""
        # Get seasons
        response = admin_client.get("/v1/seasons")
        assert response.status_code == 200
        assert "seasons" in response.json()

    def test_non_admin_cannot_access_seasons(self, non_admin_client):
        """Test that non-admin users cannot access seasons endpoints."""
        # Get seasons - should fail
        response = non_admin_client.get("/v1/seasons")
        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]

    def test_unauthenticated_cannot_access_seasons(self, unauthenticated_client):
        """Test that unauthenticated users cannot access seasons endpoints."""
        # Get seasons - should fail with 401
        response = unauthenticated_client.get("/v1/seasons")
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]

    def test_non_admin_cannot_create_season(self, non_admin_client):
        """Test that non-admin users cannot create seasons."""
        season_data = {
            "name": "Test Season",
            "code": "TEST2025",
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
        }

        response = non_admin_client.post("/v1/seasons", json=season_data)
        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]

    def test_non_admin_cannot_update_season(self, non_admin_client):
        """Test that non-admin users cannot update seasons."""
        update_data = {"name": "Updated Season"}
        response = non_admin_client.put("/v1/seasons/1", json=update_data)
        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]

    def test_non_admin_cannot_activate_season(self, non_admin_client):
        """Test that non-admin users cannot activate seasons."""
        response = non_admin_client.post("/v1/seasons/1/activate")
        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]

    def test_non_admin_cannot_delete_season(self, non_admin_client):
        """Test that non-admin users cannot delete seasons."""
        response = non_admin_client.delete("/v1/seasons/1")
        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]

    def test_admin_seasons_page_loads_for_all_users(self, non_admin_client):
        """Test that the admin seasons HTML page loads (auth is handled client-side)."""
        response = non_admin_client.get("/admin/seasons")
        assert response.status_code == 200
        # The page loads but client-side JS will redirect if no admin token
        assert "Season Management" in response.text
