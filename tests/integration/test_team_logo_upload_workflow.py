"""Integration tests for team logo upload workflow."""

import io
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.data_access.models import Team
from app.services.image_processing_service import ImageProcessingService


class TestTeamLogoUploadWorkflow:
    """Integration tests for the complete team logo upload workflow."""

    @pytest.fixture
    def client(self, test_db_file_session):
        """Create a FastAPI test client with isolated database."""
        from app.auth.dependencies import get_current_user
        from app.auth.models import User
        from app.web_ui.api import app
        from app.web_ui.dependencies import get_db

        def override_get_db():
            return test_db_file_session

        def mock_current_user():
            return User(id=1, username="testuser", email="test@example.com", role="admin", is_active=True)

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = mock_current_user
        client = TestClient(app)
        yield client
        app.dependency_overrides.clear()

    @pytest.fixture
    def unauthenticated_client(self, test_db_file_session):
        """Create a FastAPI test client without authentication override."""
        from app.web_ui.api import app
        from app.web_ui.dependencies import get_db

        def override_get_db():
            return test_db_file_session

        app.dependency_overrides[get_db] = override_get_db
        # Note: no auth override here, so authentication will be required
        client = TestClient(app)
        yield client
        app.dependency_overrides.clear()

    @pytest.fixture
    def test_team(self, test_db_file_session):
        """Create a test team."""
        team = Team(name="Test Team", display_name="Test Team Display")
        test_db_file_session.add(team)
        test_db_file_session.commit()
        test_db_file_session.refresh(team)
        return team

    @pytest.fixture
    def authenticated_headers(self):
        """Get headers for authenticated requests."""
        # This would normally create actual auth tokens
        # For testing purposes, we'll mock the authentication
        return {"Authorization": "Bearer test-token"}

    @pytest.fixture
    def valid_image_file(self, test_image_blue):
        """Create a valid image file for testing."""
        return test_image_blue

    @pytest.fixture
    def invalid_image_file(self):
        """Create an invalid file for testing."""
        return ("test.txt", io.BytesIO(b"not an image"), "text/plain")

    @pytest.fixture
    def oversized_image_file(self, oversized_test_image):
        """Create an oversized image file for testing."""
        return oversized_test_image

    def test_upload_team_logo_complete_workflow(self, client, test_team, authenticated_headers, valid_image_file):
        """Test the complete team logo upload workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(ImageProcessingService, "get_team_logo_directory") as mock_get_dir:
                mock_get_dir.return_value = Path(temp_dir) / "teams" / str(test_team.id)

                # Authentication is already mocked in the client fixture

                # Upload logo
                response = client.post(
                    f"/v1/teams/{test_team.id}/logo",
                    files={"file": valid_image_file},
                    headers=authenticated_headers,
                )

                # Check response
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["message"] == "Logo uploaded successfully"
                assert "logo_urls" in data
                assert "original" in data["logo_urls"]
                assert "120x120" in data["logo_urls"]
                assert "64x64" in data["logo_urls"]

                # Verify files were created
                team_dir = Path(temp_dir) / "teams" / str(test_team.id)
                assert (team_dir / "original" / "logo.jpg").exists()
                assert (team_dir / "120x120" / "logo.jpg").exists()
                assert (team_dir / "64x64" / "logo.jpg").exists()

                # Verify image dimensions
                with Image.open(team_dir / "120x120" / "logo.jpg") as img:
                    assert img.size == (120, 120)

                with Image.open(team_dir / "64x64" / "logo.jpg") as img:
                    assert img.size == (64, 64)

    def test_upload_team_logo_unauthenticated(self, unauthenticated_client, test_team, valid_image_file):
        """Test team logo upload without authentication."""
        response = unauthenticated_client.post(f"/v1/teams/{test_team.id}/logo", files={"file": valid_image_file})

        # Should require authentication
        assert response.status_code in [401, 403]

    def test_upload_team_logo_invalid_team(self, client, authenticated_headers, valid_image_file):
        """Test team logo upload for non-existent team."""
        response = client.post("/v1/teams/99999/logo", files={"file": valid_image_file}, headers=authenticated_headers)

        assert response.status_code == 404
        data = response.json()
        assert "Team not found" in data["detail"]

    def test_upload_team_logo_invalid_file(self, client, test_team, authenticated_headers, invalid_image_file):
        """Test team logo upload with invalid file."""
        response = client.post(
            f"/v1/teams/{test_team.id}/logo", files={"file": invalid_image_file}, headers=authenticated_headers
        )

        assert response.status_code == 400
        data = response.json()
        assert "Invalid file type" in data["detail"]

    def test_upload_team_logo_oversized_file(self, client, test_team, authenticated_headers, oversized_image_file):
        """Test team logo upload with oversized file."""
        response = client.post(
            f"/v1/teams/{test_team.id}/logo", files={"file": oversized_image_file}, headers=authenticated_headers
        )

        assert response.status_code == 400
        data = response.json()
        assert "File too large" in data["detail"]

    def test_delete_team_logo_complete_workflow(self, client, test_team, authenticated_headers, valid_image_file):
        """Test the complete team logo deletion workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(ImageProcessingService, "get_team_logo_directory") as mock_get_dir:
                mock_get_dir.return_value = Path(temp_dir) / "teams" / str(test_team.id)

                # Authentication is already mocked in the client fixture

                # First upload a logo
                client.post(
                    f"/v1/teams/{test_team.id}/logo",
                    files={"file": valid_image_file},
                    headers=authenticated_headers,
                )

                # Verify logo exists
                team_dir = Path(temp_dir) / "teams" / str(test_team.id)
                assert team_dir.exists()

                # Delete the logo
                response = client.delete(f"/v1/teams/{test_team.id}/logo", headers=authenticated_headers)

                # Check response
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["message"] == "Logo deleted successfully"

                # Verify files were deleted
                assert not team_dir.exists()

    def test_delete_team_logo_no_existing_logo(self, client, test_team, authenticated_headers):
        """Test deleting logo when team has no logo."""
        response = client.delete(f"/v1/teams/{test_team.id}/logo", headers=authenticated_headers)

        assert response.status_code == 400
        data = response.json()
        assert "Team has no logo to delete" in data["detail"]

    def test_upload_logo_replaces_existing(self, client, test_team, authenticated_headers):
        """Test that uploading a new logo replaces the existing one."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(ImageProcessingService, "get_team_logo_directory") as mock_get_dir:
                mock_get_dir.return_value = Path(temp_dir) / "teams" / str(test_team.id)

                # Authentication is already mocked in the client fixture

                # Upload first logo (JPEG) - use blue test image
                img1 = Image.new("RGB", (100, 100), color="blue")
                img1_bytes = io.BytesIO()
                img1.save(img1_bytes, format="JPEG")
                img1_bytes.seek(0)
                file1 = ("logo1.jpg", img1_bytes, "image/jpeg")

                response1 = client.post(
                    f"/v1/teams/{test_team.id}/logo", files={"file": file1}, headers=authenticated_headers
                )
                assert response1.status_code == 200

                # Verify first logo exists
                team_dir = Path(temp_dir) / "teams" / str(test_team.id)
                assert (team_dir / "original" / "logo.jpg").exists()

                # Upload second logo (PNG)
                img2 = Image.new("RGB", (100, 100), color="blue")
                img2_bytes = io.BytesIO()
                img2.save(img2_bytes, format="PNG")
                img2_bytes.seek(0)
                file2 = ("logo2.png", img2_bytes, "image/png")

                response2 = client.post(
                    f"/v1/teams/{test_team.id}/logo", files={"file": file2}, headers=authenticated_headers
                )
                assert response2.status_code == 200

                # Verify second logo exists and first is gone
                assert not (team_dir / "original" / "logo.jpg").exists()
                assert (team_dir / "original" / "logo.png").exists()

    def test_logo_url_generation_after_upload(self, client, test_team, authenticated_headers, valid_image_file):
        """Test that logo URLs are properly generated after upload."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(ImageProcessingService, "get_team_logo_directory") as mock_get_dir:
                mock_get_dir.return_value = Path(temp_dir) / "teams" / str(test_team.id)

                # Authentication is already mocked in the client fixture

                # Upload logo
                response = client.post(
                    f"/v1/teams/{test_team.id}/logo",
                    files={"file": valid_image_file},
                    headers=authenticated_headers,
                )

                data = response.json()
                logo_urls = data["logo_urls"]

                # Verify URL structure
                for size, url in logo_urls.items():
                    assert url.startswith("/uploads/")
                    assert f"teams/{test_team.id}" in url
                    assert size in url
                    assert "logo.jpg" in url

                # Test URL helper function
                from app.web_ui.templates_config import team_logo_url

                # Create mock team object
                mock_team = type("Team", (), {"id": test_team.id})()

                # Test different sizes
                url_120 = team_logo_url(mock_team, "120x120")
                url_64 = team_logo_url(mock_team, "64x64")
                url_original = team_logo_url(mock_team, "original")

                assert url_120 == logo_urls["120x120"]
                assert url_64 == logo_urls["64x64"]
                assert url_original == logo_urls["original"]
