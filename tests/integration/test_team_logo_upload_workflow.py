"""Integration tests for team logo upload workflow."""

import io
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from app.config import UPLOADS_URL_PREFIX
from app.data_access.models import Team
from app.services.image_processing_service import ImageProcessingService


class TestTeamLogoUploadWorkflow:
    """Integration tests for the complete team logo upload workflow."""

    @pytest.fixture
    def client(self, isolated_client):
        """Use the isolated client from conftest."""
        return isolated_client

    @pytest.fixture
    def unauthenticated_client(self, isolated_unauthenticated_client):
        """Use the isolated unauthenticated client from conftest."""
        return isolated_unauthenticated_client

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
            with patch.object(ImageProcessingService, "get_image_directory") as mock_get_dir:
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
                assert "logo_url" in data
                assert data["logo_url"].startswith(UPLOADS_URL_PREFIX)

                # Verify file was created
                team_dir = Path(temp_dir) / "teams" / str(test_team.id)
                assert (team_dir / "logo.jpg").exists()

                # Verify image dimensions (should be resized to fit within 250x250)
                with Image.open(team_dir / "logo.jpg") as img:
                    assert img.size[0] <= 250
                    assert img.size[1] <= 250

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
            with patch.object(ImageProcessingService, "get_image_directory") as mock_get_dir:
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
            with patch.object(ImageProcessingService, "get_image_directory") as mock_get_dir:
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
                assert (team_dir / "logo.jpg").exists()

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
                assert not (team_dir / "logo.jpg").exists()
                assert (team_dir / "logo.png").exists()

    def test_logo_url_generation_after_upload(
        self, client, test_team, authenticated_headers, valid_image_file, test_db_file_session, monkeypatch
    ):
        """Test that logo URLs are properly generated after upload."""
        # Import and clear caches FIRST, before any other imports
        import app.web_ui.templates_config as templates_config_module

        # Force clear ALL caches before starting
        if hasattr(templates_config_module, "_get_cached_entity_image_data"):
            templates_config_module._get_cached_entity_image_data.cache_clear()
        if hasattr(templates_config_module, "_check_file_exists"):
            templates_config_module._check_file_exists.cache_clear()

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(ImageProcessingService, "get_image_directory") as mock_get_dir:
                mock_get_dir.return_value = Path(temp_dir) / "teams" / str(test_team.id)

                # Also mock update_team_logo_filename to return expected filename
                with patch.object(ImageProcessingService, "update_team_logo_filename") as mock_update_filename:
                    mock_update_filename.return_value = f"teams/{test_team.id}/logo.jpg"

                    # Authentication is already mocked in the client fixture

                    # Upload logo
                    response = client.post(
                        f"/v1/teams/{test_team.id}/logo",
                        files={"file": valid_image_file},
                        headers=authenticated_headers,
                    )

                    data = response.json()
                    logo_url = data["logo_url"]

                    # Verify URL structure
                    assert logo_url.startswith(UPLOADS_URL_PREFIX)
                    assert f"teams/{test_team.id}" in logo_url
                    assert "logo.jpg" in logo_url

                    # Test URL helper function
                    from app import config
                    from app.web_ui.templates_config import (
                        _get_team_logo_data_uncached,
                        clear_team_logo_cache,
                        team_logo_url,
                    )

                    # Clear cache again after imports
                    clear_team_logo_cache()

                    # Patch get_db_session to use the test session
                    from contextlib import contextmanager

                    @contextmanager
                    def test_get_db_session():
                        try:
                            yield test_db_file_session
                        finally:
                            pass

                    import app.data_access.db_session as db_session_module

                    monkeypatch.setattr(db_session_module, "get_db_session", test_get_db_session)

                    # Patch the cached function to use uncached version for integration tests
                    import app.web_ui.templates_config as templates_config_module

                    monkeypatch.setattr(
                        templates_config_module,
                        "_get_cached_entity_image_data",
                        lambda entity_id, entity_type: _get_team_logo_data_uncached(entity_id)
                        if entity_type == "team"
                        else None,
                    )

                    # Patch the UPLOAD_DIR to point to our temp directory
                    with patch.object(config.settings, "UPLOAD_DIR", temp_dir):
                        # Refresh team from database to get updated logo_filename
                        test_db_file_session.refresh(test_team)

                        # Test URL generation
                        generated_url = team_logo_url(test_team)
                        assert generated_url == logo_url
