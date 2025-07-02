"""Integration tests for team logo upload workflow."""

import io
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from app.config import UPLOADS_URL_PREFIX
from app.services.image_processing_service import ImageProcessingService


class TestTeamLogoUploadWorkflow:
    """Integration tests for the complete team logo upload workflow."""

    # Use shared test team fixture instead of custom one

    @pytest.fixture
    def invalid_image_file(self):
        """Create an invalid file for testing."""
        return ("test.txt", io.BytesIO(b"not an image"), "text/plain")

    def test_upload_team_logo_complete_workflow(self, authenticated_client, shared_test_team, test_image_blue, clear_image_caches):
        """Test the complete team logo upload workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(ImageProcessingService, "get_image_directory") as mock_get_dir:
                mock_get_dir.return_value = Path(temp_dir) / "teams" / str(shared_test_team.id)

                # Upload logo
                response = authenticated_client.post(
                    f"/v1/teams/{shared_test_team.id}/logo",
                    files={"file": test_image_blue},
                )

                # Check response
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["message"] == "Logo uploaded successfully"
                assert "logo_url" in data
                assert data["logo_url"].startswith(UPLOADS_URL_PREFIX)

                # Verify file was created
                team_dir = Path(temp_dir) / "teams" / str(shared_test_team.id)
                assert (team_dir / "logo.jpg").exists()

                # Verify image dimensions (should be resized to fit within 250x250)
                with Image.open(team_dir / "logo.jpg") as img:
                    assert img.size[0] <= 250
                    assert img.size[1] <= 250

    def test_upload_team_logo_unauthenticated(self, unauthenticated_client, shared_test_team, test_image_blue):
        """Test team logo upload without authentication."""
        response = unauthenticated_client.post(f"/v1/teams/{shared_test_team.id}/logo", files={"file": test_image_blue})

        # Should require authentication
        assert response.status_code in [401, 403]

    def test_upload_team_logo_invalid_team(self, authenticated_client, test_image_blue):
        """Test team logo upload for non-existent team."""
        response = authenticated_client.post("/v1/teams/99999/logo", files={"file": test_image_blue})

        assert response.status_code == 404
        data = response.json()
        assert "Team not found" in data["detail"]

    def test_upload_team_logo_invalid_file(self, authenticated_client, shared_test_team, invalid_image_file):
        """Test team logo upload with invalid file."""
        response = authenticated_client.post(
            f"/v1/teams/{shared_test_team.id}/logo", files={"file": invalid_image_file}
        )

        assert response.status_code == 400
        data = response.json()
        assert "Invalid file type" in data["detail"]

    def test_upload_team_logo_oversized_file(self, authenticated_client, shared_test_team, oversized_test_image):
        """Test team logo upload with oversized file."""
        response = authenticated_client.post(
            f"/v1/teams/{shared_test_team.id}/logo", files={"file": oversized_test_image}
        )

        assert response.status_code == 400
        data = response.json()
        assert "File too large" in data["detail"]

    def test_delete_team_logo_complete_workflow(self, authenticated_client, shared_test_team, test_image_blue):
        """Test the complete team logo deletion workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(ImageProcessingService, "get_image_directory") as mock_get_dir:
                mock_get_dir.return_value = Path(temp_dir) / "teams" / str(shared_test_team.id)

                # First upload a logo
                authenticated_client.post(
                    f"/v1/teams/{shared_test_team.id}/logo",
                    files={"file": test_image_blue},
                )

                # Verify logo exists
                team_dir = Path(temp_dir) / "teams" / str(shared_test_team.id)
                assert team_dir.exists()

                # Delete the logo
                response = authenticated_client.delete(f"/v1/teams/{shared_test_team.id}/logo")

                # Check response
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["message"] == "Logo deleted successfully"

                # Verify files were deleted
                assert not team_dir.exists()

    def test_delete_team_logo_no_existing_logo(self, authenticated_client, shared_test_team):
        """Test deleting logo when team has no logo."""
        response = authenticated_client.delete(f"/v1/teams/{shared_test_team.id}/logo")

        assert response.status_code == 400
        data = response.json()
        assert "Team has no logo to delete" in data["detail"]

    def test_upload_logo_replaces_existing(self, authenticated_client, shared_test_team):
        """Test that uploading a new logo replaces the existing one."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(ImageProcessingService, "get_image_directory") as mock_get_dir:
                mock_get_dir.return_value = Path(temp_dir) / "teams" / str(shared_test_team.id)

                # Upload first logo (JPEG) - use blue test image
                img1 = Image.new("RGB", (100, 100), color="blue")
                img1_bytes = io.BytesIO()
                img1.save(img1_bytes, format="JPEG")
                img1_bytes.seek(0)
                file1 = ("logo1.jpg", img1_bytes, "image/jpeg")

                response1 = authenticated_client.post(f"/v1/teams/{shared_test_team.id}/logo", files={"file": file1})
                assert response1.status_code == 200

                # Verify first logo exists
                team_dir = Path(temp_dir) / "teams" / str(shared_test_team.id)
                assert (team_dir / "logo.jpg").exists()

                # Upload second logo (PNG)
                img2 = Image.new("RGB", (100, 100), color="blue")
                img2_bytes = io.BytesIO()
                img2.save(img2_bytes, format="PNG")
                img2_bytes.seek(0)
                file2 = ("logo2.png", img2_bytes, "image/png")

                response2 = authenticated_client.post(f"/v1/teams/{shared_test_team.id}/logo", files={"file": file2})
                assert response2.status_code == 200

                # Verify second logo exists and first is gone
                assert not (team_dir / "logo.jpg").exists()
                assert (team_dir / "logo.png").exists()

    def test_logo_url_generation_after_upload(
        self, authenticated_client, shared_test_team, test_image_blue, integration_db_session, monkeypatch, clear_image_caches
    ):
        """Test that logo URLs are properly generated after upload."""
        # Cache clearing is handled by clear_image_caches fixture
        import app.web_ui.templates_config as templates_config_module

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(ImageProcessingService, "get_image_directory") as mock_get_dir:
                mock_get_dir.return_value = Path(temp_dir) / "teams" / str(shared_test_team.id)

                # Also mock update_team_logo_filename to return expected filename
                with patch.object(ImageProcessingService, "update_team_logo_filename") as mock_update_filename:
                    mock_update_filename.return_value = f"teams/{shared_test_team.id}/logo.jpg"

                    # Upload logo
                    response = authenticated_client.post(
                        f"/v1/teams/{shared_test_team.id}/logo",
                        files={"file": test_image_blue},
                    )

                    data = response.json()
                    logo_url = data["logo_url"]

                    # Verify URL structure
                    assert logo_url.startswith(UPLOADS_URL_PREFIX)
                    assert f"teams/{shared_test_team.id}" in logo_url
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
                            yield integration_db_session
                        finally:
                            pass

                    import app.data_access.db_session as db_session_module

                    monkeypatch.setattr(db_session_module, "get_db_session", test_get_db_session)

                    # Patch the cached function to use uncached version for integration tests
                    import app.web_ui.templates_config as templates_config_module

                    # Cache clearing is handled by clear_image_caches fixture

                    monkeypatch.setattr(
                        templates_config_module,
                        "_get_cached_entity_image_data",
                        lambda entity_id, entity_type: _get_team_logo_data_uncached(entity_id)
                        if entity_type == "team"
                        else None,
                    )

                    # Patch both the UPLOAD_DIR setting and the module-level UPLOADS_DIR
                    from app.services import image_processing_service

                    with (
                        patch.object(config.settings, "UPLOAD_DIR", temp_dir),
                        patch.object(image_processing_service, "UPLOADS_DIR", Path(temp_dir)),
                    ):
                        # Refresh team from database to get updated logo_filename
                        integration_db_session.refresh(shared_test_team)

                        # Test URL generation
                        generated_url = team_logo_url(shared_test_team)
                        assert generated_url == logo_url
