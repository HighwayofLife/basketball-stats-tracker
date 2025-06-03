"""Integration tests for cookie-based authentication."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.service import AuthService
from app.dependencies import get_db
from app.web_ui.api import app


class TestCookieAuthentication:
    """Test cookie-based authentication flow."""

    @pytest.fixture
    def test_user(self, test_db_file_session: Session):
        """Create a test user."""
        auth_service = AuthService(test_db_file_session)
        user = auth_service.create_user(
            username="cookietest", email="cookie@test.com", password="testpassword123", full_name="Cookie Test User"
        )
        test_db_file_session.commit()
        return user

    def test_login_sets_cookies(self, test_user: User, test_db_file_session: Session):
        """Test that login sets authentication cookies."""

        # Override the database dependency
        def override_get_db():
            yield test_db_file_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            client = TestClient(app)

            # Login
            response = client.post("/auth/token", data={"username": "cookietest", "password": "testpassword123"})

            assert response.status_code == 200

            # Check response contains tokens
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "bearer"

            # Check cookies were set
            assert "access_token" in response.cookies
            assert "refresh_token" in response.cookies

            # Verify cookie attributes
            access_cookie = response.cookies.get("access_token")
            assert access_cookie is not None
        finally:
            app.dependency_overrides.clear()

    def test_cookie_authentication_works(self, test_user: User, test_db_file_session: Session):
        """Test that cookie authentication actually works."""

        # Override the database dependency
        def override_get_db():
            yield test_db_file_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            client = TestClient(app)

            # Login first
            login_response = client.post("/auth/token", data={"username": "cookietest", "password": "testpassword123"})
            assert login_response.status_code == 200

            # Check cookies were set
            assert "access_token" in login_response.cookies

            # Access an authenticated API endpoint
            # Note: TestClient doesn't automatically send cookies between requests
            # We need to manually pass them
            response = client.get("/auth/me", cookies={"access_token": login_response.cookies["access_token"]})
            assert response.status_code == 200

            # Verify user data
            data = response.json()
            assert data["username"] == "cookietest"
            assert data["email"] == "cookie@test.com"
        finally:
            app.dependency_overrides.clear()

    def test_logout_clears_cookies(self, test_user: User, test_db_file_session: Session):
        """Test that logout clears authentication cookies."""

        # Override the database dependency
        def override_get_db():
            yield test_db_file_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            client = TestClient(app)

            # Login first
            login_response = client.post("/auth/token", data={"username": "cookietest", "password": "testpassword123"})
            assert login_response.status_code == 200
            assert "access_token" in login_response.cookies

            # Logout
            response = client.get("/logout", follow_redirects=False)
            assert response.status_code == 200  # Now returns HTML page instead of redirect

            # Check that cookies are cleared
            # The delete_cookie sets the cookie with empty value and max_age=0
            set_cookie_headers = response.headers.get_list("set-cookie")
            access_token_cleared = False
            for header in set_cookie_headers:
                if "access_token=" in header and ("Max-Age=0" in header or "expires=Thu, 01 Jan 1970" in header):
                    access_token_cleared = True
                    break
            assert access_token_cleared
        finally:
            app.dependency_overrides.clear()

    def test_mixed_auth_bearer_token_and_cookie(self, test_user: User, test_db_file_session: Session):
        """Test that both bearer token and cookie authentication work."""

        # Override the database dependency
        def override_get_db():
            yield test_db_file_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            client = TestClient(app)

            # Login to get tokens
            login_response = client.post("/auth/token", data={"username": "cookietest", "password": "testpassword123"})
            assert login_response.status_code == 200
            token = login_response.json()["access_token"]

            # Test with bearer token
            response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
            assert response.status_code == 200
            assert response.json()["username"] == "cookietest"

            # Test with cookie
            response = client.get("/auth/me", cookies={"access_token": token})
            assert response.status_code == 200
            assert response.json()["username"] == "cookietest"
        finally:
            app.dependency_overrides.clear()

    def test_secure_cookie_in_production(self, test_user: User, test_db_file_session: Session):
        """Test that cookies are set with secure attributes."""

        # Override the database dependency
        def override_get_db():
            yield test_db_file_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            client = TestClient(app)

            # Login
            response = client.post("/auth/token", data={"username": "cookietest", "password": "testpassword123"})

            assert response.status_code == 200

            # Check cookie attributes in headers
            set_cookie_headers = response.headers.get_list("set-cookie")
            access_token_header = None
            for header in set_cookie_headers:
                if "access_token=" in header:
                    access_token_header = header
                    break

            assert access_token_header is not None
            # Check security attributes
            assert "HttpOnly" in access_token_header
            assert "Secure" in access_token_header
            assert "SameSite=Strict" in access_token_header
        finally:
            app.dependency_overrides.clear()
