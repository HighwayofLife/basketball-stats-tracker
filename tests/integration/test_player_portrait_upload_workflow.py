"""Integration tests for player portrait upload workflow."""

import io
from pathlib import Path

import pytest
from PIL import Image

from app.data_access import models
from app.services.image_processing_service import ImageProcessingService, ImageType


@pytest.mark.integration
class TestPlayerPortraitUploadWorkflow:
    """Test the complete player portrait upload workflow."""

    # Use shared test team and player fixtures instead of custom ones

    def get_test_image_bytes(self, image_tuple) -> bytes:
        """Get test image bytes from fixture tuple."""
        filename, img_bytes, mime_type = image_tuple
        img_bytes.seek(0)
        return img_bytes.getvalue()

    def test_upload_player_portrait_success(self, authenticated_client, shared_test_player, integration_db_session, test_image_red):
        """Test successful player portrait upload."""
        # Create test image
        image_data = self.get_test_image_bytes(test_image_red)

        # Upload portrait
        response = authenticated_client.post(
            f"/v1/players/{shared_test_player.id}/portrait",
            files={"file": ("portrait.jpg", image_data, "image/jpeg")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "portrait_url" in data
        assert f"players/{shared_test_player.id}/portrait.jpg" in data["portrait_url"]

        # Verify file was created
        portrait_path = (
            Path(ImageProcessingService.get_image_directory(shared_test_player.id, ImageType.PLAYER_PORTRAIT)) / "portrait.jpg"
        )
        assert portrait_path.exists()

        # Verify database was updated
        integration_db_session.refresh(shared_test_player)
        assert shared_test_player.thumbnail_image is not None
        assert f"players/{shared_test_player.id}/portrait.jpg" in shared_test_player.thumbnail_image

        # Verify image was resized
        with Image.open(portrait_path) as img:
            assert img.width <= 250
            assert img.height <= 250

    def test_upload_player_portrait_png(self, authenticated_client, shared_test_player, test_image_green):
        """Test uploading PNG format portrait."""
        # Create test PNG image
        image_data = self.get_test_image_bytes(test_image_green)

        # Upload portrait
        response = authenticated_client.post(
            f"/v1/players/{shared_test_player.id}/portrait",
            files={"file": ("portrait.png", image_data, "image/png")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "portrait.png" in data["portrait_url"]

    def test_upload_player_portrait_replaces_existing(self, authenticated_client, shared_test_player, test_image_red, test_image_green):
        """Test that uploading a new portrait replaces the existing one."""
        # Upload first portrait
        image_data1 = self.get_test_image_bytes(test_image_red)
        response1 = authenticated_client.post(
            f"/v1/players/{shared_test_player.id}/portrait",
            files={"file": ("first.jpg", image_data1, "image/jpeg")},
        )
        assert response1.status_code == 200

        # Verify first portrait exists
        first_path = (
            Path(ImageProcessingService.get_image_directory(shared_test_player.id, ImageType.PLAYER_PORTRAIT)) / "portrait.jpg"
        )
        assert first_path.exists()

        # Upload second portrait with different format
        image_data2 = self.get_test_image_bytes(test_image_green)
        response2 = authenticated_client.post(
            f"/v1/players/{shared_test_player.id}/portrait",
            files={"file": ("second.png", image_data2, "image/png")},
        )
        assert response2.status_code == 200

        # Verify first portrait is gone and second exists
        assert not first_path.exists()
        second_path = (
            Path(ImageProcessingService.get_image_directory(shared_test_player.id, ImageType.PLAYER_PORTRAIT)) / "portrait.png"
        )
        assert second_path.exists()

    def test_upload_player_portrait_unauthorized(self, unauthenticated_client, shared_test_player, test_image_red):
        """Test portrait upload without authentication."""
        image_data = self.get_test_image_bytes(test_image_red)

        response = unauthenticated_client.post(
            f"/v1/players/{shared_test_player.id}/portrait",
            files={"file": ("portrait.jpg", image_data, "image/jpeg")},
        )

        assert response.status_code == 401

    def test_upload_player_portrait_invalid_file_type(self, authenticated_client, shared_test_player):
        """Test portrait upload with invalid file type."""
        # Create a text file
        text_data = b"This is not an image"

        response = authenticated_client.post(
            f"/v1/players/{shared_test_player.id}/portrait",
            files={"file": ("test.txt", text_data, "text/plain")},
        )

        assert response.status_code == 422
        data = response.json()
        assert data["detail"]["error"] == "INVALID_FILE_TYPE"

    def test_upload_player_portrait_file_too_large(self, authenticated_client, shared_test_player):
        """Test portrait upload with oversized file."""
        # Create a large image (over 5MB)
        large_data = b"x" * (6 * 1024 * 1024)

        response = authenticated_client.post(
            f"/v1/players/{shared_test_player.id}/portrait",
            files={"file": ("large.jpg", large_data, "image/jpeg")},
        )

        assert response.status_code == 422
        data = response.json()
        assert data["detail"]["error"] == "FILE_TOO_LARGE"

    def test_upload_player_portrait_nonexistent_player(self, authenticated_client, test_image_red):
        """Test portrait upload for non-existent player."""
        image_data = self.get_test_image_bytes(test_image_red)

        response = authenticated_client.post(
            "/v1/players/99999/portrait",
            files={"file": ("portrait.jpg", image_data, "image/jpeg")},
        )

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"] == "PLAYER_NOT_FOUND"

    def test_delete_player_portrait_success(self, authenticated_client, shared_test_player, integration_db_session, test_image_red):
        """Test successful player portrait deletion."""
        # First upload a portrait
        image_data = self.get_test_image_bytes(test_image_red)
        upload_response = authenticated_client.post(
            f"/v1/players/{shared_test_player.id}/portrait",
            files={"file": ("portrait.jpg", image_data, "image/jpeg")},
        )
        assert upload_response.status_code == 200

        # Verify portrait exists
        portrait_path = (
            Path(ImageProcessingService.get_image_directory(shared_test_player.id, ImageType.PLAYER_PORTRAIT)) / "portrait.jpg"
        )
        assert portrait_path.exists()

        # Delete portrait
        delete_response = authenticated_client.delete(
            f"/v1/players/{shared_test_player.id}/portrait",
        )

        assert delete_response.status_code == 200
        data = delete_response.json()
        assert data["success"] is True
        assert data["message"] == "Portrait deleted successfully"

        # Verify file was deleted
        assert not portrait_path.exists()

        # Verify database was updated
        integration_db_session.refresh(shared_test_player)
        assert shared_test_player.thumbnail_image is None

    def test_delete_player_portrait_no_portrait(self, authenticated_client, shared_test_player):
        """Test deleting portrait when player has no portrait."""
        response = authenticated_client.delete(
            f"/v1/players/{shared_test_player.id}/portrait",
        )

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"] == "NO_PORTRAIT_TO_DELETE"

    def test_delete_player_portrait_unauthorized(self, unauthenticated_client, shared_test_player):
        """Test portrait deletion without authentication."""
        response = unauthenticated_client.delete(f"/v1/players/{shared_test_player.id}/portrait")

        assert response.status_code == 401

    def test_player_detail_page_shows_portrait(self, authenticated_client, shared_test_player, test_image_red):
        """Test that player detail page shows uploaded portrait."""
        # Upload a portrait
        image_data = self.get_test_image_bytes(test_image_red)
        upload_response = authenticated_client.post(
            f"/v1/players/{shared_test_player.id}/portrait",
            files={"file": ("portrait.jpg", image_data, "image/jpeg")},
        )
        assert upload_response.status_code == 200

        # Get player stats which includes portrait info
        stats_response = authenticated_client.get(f"/v1/players/{shared_test_player.id}/stats")
        assert stats_response.status_code == 200

        stats_data = stats_response.json()
        assert stats_data["player"]["thumbnail_image"] is not None
        assert f"players/{shared_test_player.id}/portrait.jpg" in stats_data["player"]["thumbnail_image"]

    def test_legacy_upload_endpoint_compatibility(
        self, authenticated_client, shared_test_player, integration_db_session, test_image_red
    ):
        """Test that legacy upload-image endpoint still works."""
        image_data = self.get_test_image_bytes(test_image_red)

        # Use legacy endpoint
        response = authenticated_client.post(
            f"/v1/players/{shared_test_player.id}/upload-image",
            files={"file": ("portrait.jpg", image_data, "image/jpeg")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify portrait was uploaded
        integration_db_session.refresh(shared_test_player)
        assert shared_test_player.thumbnail_image is not None

    def test_portrait_url_template_helper(self, authenticated_client, shared_test_player, integration_db_session):
        """Test that portrait URL is correctly generated in templates."""
        from unittest.mock import patch

        from app.web_ui.templates_config import player_portrait_url

        # Clean up any existing portrait files and database records first
        shared_test_player.thumbnail_image = None
        integration_db_session.commit()

        # Clean up any existing files
        portrait_dir = ImageProcessingService.get_image_directory(shared_test_player.id, ImageType.PLAYER_PORTRAIT)
        if portrait_dir.exists():
            import shutil

            shutil.rmtree(portrait_dir)

        # Clear cache
        from app.web_ui.templates_config import clear_player_portrait_cache

        clear_player_portrait_cache()

        # Mock the database session to use our test session
        with patch("app.data_access.db_session.get_db_session") as mock_get_db:
            # Make the context manager return our test session
            mock_get_db.return_value.__enter__.return_value = integration_db_session

            # Test with no portrait
            url = player_portrait_url(shared_test_player)
            assert url is None

            # Upload portrait
            # Simulate portrait upload by updating database
            shared_test_player.thumbnail_image = f"players/{shared_test_player.id}/portrait.jpg"
            integration_db_session.add(shared_test_player)
            integration_db_session.commit()

            # Create the actual file
            portrait_dir = ImageProcessingService.get_image_directory(shared_test_player.id, ImageType.PLAYER_PORTRAIT)
            portrait_dir.mkdir(parents=True, exist_ok=True)
            portrait_path = portrait_dir / "portrait.jpg"

            img = Image.new("RGB", (200, 200), color="blue")
            img.save(portrait_path, "JPEG")

            # Clear cache to get fresh data
            clear_player_portrait_cache()

            # Test portrait URL generation - refresh player from database to get real object
            integration_db_session.refresh(shared_test_player)
            url = player_portrait_url(shared_test_player)
            assert url is not None
            assert f"/uploads/players/{shared_test_player.id}/portrait.jpg" in url
