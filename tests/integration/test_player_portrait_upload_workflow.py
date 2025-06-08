"""Integration tests for player portrait upload workflow."""

import io
import os
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy.orm import Session

from app.auth.jwt_handler import create_access_token
from app.auth.models import User
from app.data_access import models
from app.data_access.db_session import get_db_session
from app.main import app
from app.services.image_processing_service import ImageProcessingService, ImageType


@pytest.mark.integration
class TestPlayerPortraitUploadWorkflow:
    """Test the complete player portrait upload workflow."""

    @pytest.fixture
    def test_user(self, test_db_file_session):
        """Create a test user."""
        from app.auth.jwt_handler import get_password_hash
        from app.auth.models import UserRole
        
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password=get_password_hash("testpass123"),
            is_active=True,
            role=UserRole.USER,
            provider="local",
        )
        test_db_file_session.add(user)
        test_db_file_session.commit()
        test_db_file_session.refresh(user)
        return user

    @pytest.fixture
    def auth_headers(self, test_user: User) -> dict:
        """Create authentication headers for test user."""
        access_token = create_access_token(data={"sub": test_user.username})
        return {"Authorization": f"Bearer {access_token}"}

    @pytest.fixture
    def test_team(self, test_db_file_session):
        """Create a test team."""
        from app.data_access.models import Team
        team = Team(name="Test Team", display_name="Test Team Display")
        test_db_file_session.add(team)
        test_db_file_session.commit()
        test_db_file_session.refresh(team)
        return team

    @pytest.fixture
    def test_player(self, test_team: models.Team, test_db_file_session) -> models.Player:
        """Create a test player."""
        player = models.Player(
            name="Test Player",
            team_id=test_team.id,
            jersey_number="23",
            position="PG",
            height=72,
            weight=180,
            year="Senior",
            is_active=True,
            is_substitute=False,
        )
        test_db_file_session.add(player)
        test_db_file_session.commit()
        test_db_file_session.refresh(player)
        return player

    def create_test_image(self, format="JPEG") -> bytes:
        """Create a test image file."""
        img = Image.new("RGB", (300, 300), color="red")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format=format)
        img_bytes.seek(0)
        return img_bytes.getvalue()

    def test_upload_player_portrait_success(self, isolated_client, auth_headers, test_player, test_db_file_session):
        """Test successful player portrait upload."""
        # Create test image
        image_data = self.create_test_image()
        
        # Upload portrait
        response = isolated_client.post(
            f"/v1/players/{test_player.id}/portrait",
            files={"file": ("portrait.jpg", image_data, "image/jpeg")},
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "portrait_url" in data
        assert f"players/{test_player.id}/portrait.jpg" in data["portrait_url"]
        
        # Verify file was created
        portrait_path = Path(ImageProcessingService.get_image_directory(
            test_player.id, 
            ImageType.PLAYER_PORTRAIT
        )) / "portrait.jpg"
        assert portrait_path.exists()
        
        # Verify database was updated
        test_db_file_session.refresh(test_player)
        assert test_player.thumbnail_image is not None
        assert f"players/{test_player.id}/portrait.jpg" in test_player.thumbnail_image
        
        # Verify image was resized
        with Image.open(portrait_path) as img:
            assert img.width <= 250
            assert img.height <= 250

    def test_upload_player_portrait_png(self, isolated_client, auth_headers, test_player):
        """Test uploading PNG format portrait."""
        # Create test PNG image
        image_data = self.create_test_image(format="PNG")
        
        # Upload portrait
        response = isolated_client.post(
            f"/v1/players/{test_player.id}/portrait",
            files={"file": ("portrait.png", image_data, "image/png")},
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "portrait.png" in data["portrait_url"]

    def test_upload_player_portrait_replaces_existing(self, isolated_client, auth_headers, test_player):
        """Test that uploading a new portrait replaces the existing one."""
        # Upload first portrait
        image_data1 = self.create_test_image()
        response1 = isolated_client.post(
            f"/v1/players/{test_player.id}/portrait",
            files={"file": ("first.jpg", image_data1, "image/jpeg")},
            headers=auth_headers,
        )
        assert response1.status_code == 200
        
        # Verify first portrait exists
        first_path = Path(ImageProcessingService.get_image_directory(
            test_player.id, 
            ImageType.PLAYER_PORTRAIT
        )) / "portrait.jpg"
        assert first_path.exists()
        
        # Upload second portrait with different format
        image_data2 = self.create_test_image(format="PNG")
        response2 = isolated_client.post(
            f"/v1/players/{test_player.id}/portrait",
            files={"file": ("second.png", image_data2, "image/png")},
            headers=auth_headers,
        )
        assert response2.status_code == 200
        
        # Verify first portrait is gone and second exists
        assert not first_path.exists()
        second_path = Path(ImageProcessingService.get_image_directory(
            test_player.id, 
            ImageType.PLAYER_PORTRAIT
        )) / "portrait.png"
        assert second_path.exists()

    def test_upload_player_portrait_unauthorized(self, isolated_unauthenticated_client, test_player):
        """Test portrait upload without authentication."""
        image_data = self.create_test_image()
        
        response = isolated_unauthenticated_client.post(
            f"/v1/players/{test_player.id}/portrait",
            files={"file": ("portrait.jpg", image_data, "image/jpeg")},
        )
        
        assert response.status_code == 401

    def test_upload_player_portrait_invalid_file_type(self, isolated_client, auth_headers, test_player):
        """Test portrait upload with invalid file type."""
        # Create a text file
        text_data = b"This is not an image"
        
        response = isolated_client.post(
            f"/v1/players/{test_player.id}/portrait",
            files={"file": ("test.txt", text_data, "text/plain")},
            headers=auth_headers,
        )
        
        assert response.status_code == 422
        data = response.json()
        assert data["detail"]["error"] == "INVALID_FILE_TYPE"

    def test_upload_player_portrait_file_too_large(self, isolated_client, auth_headers, test_player):
        """Test portrait upload with oversized file."""
        # Create a large image (over 5MB)
        large_data = b"x" * (6 * 1024 * 1024)
        
        response = isolated_client.post(
            f"/v1/players/{test_player.id}/portrait",
            files={"file": ("large.jpg", large_data, "image/jpeg")},
            headers=auth_headers,
        )
        
        assert response.status_code == 422
        data = response.json()
        assert data["detail"]["error"] == "FILE_TOO_LARGE"

    def test_upload_player_portrait_nonexistent_player(self, isolated_client, auth_headers):
        """Test portrait upload for non-existent player."""
        image_data = self.create_test_image()
        
        response = isolated_client.post(
            "/v1/players/99999/portrait",
            files={"file": ("portrait.jpg", image_data, "image/jpeg")},
            headers=auth_headers,
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"] == "PLAYER_NOT_FOUND"

    def test_delete_player_portrait_success(self, isolated_client, auth_headers, test_player, test_db_file_session):
        """Test successful player portrait deletion."""
        # First upload a portrait
        image_data = self.create_test_image()
        upload_response = isolated_client.post(
            f"/v1/players/{test_player.id}/portrait",
            files={"file": ("portrait.jpg", image_data, "image/jpeg")},
            headers=auth_headers,
        )
        assert upload_response.status_code == 200
        
        # Verify portrait exists
        portrait_path = Path(ImageProcessingService.get_image_directory(
            test_player.id, 
            ImageType.PLAYER_PORTRAIT
        )) / "portrait.jpg"
        assert portrait_path.exists()
        
        # Delete portrait
        delete_response = isolated_client.delete(
            f"/v1/players/{test_player.id}/portrait",
            headers=auth_headers,
        )
        
        assert delete_response.status_code == 200
        data = delete_response.json()
        assert data["success"] is True
        assert data["message"] == "Portrait deleted successfully"
        
        # Verify file was deleted
        assert not portrait_path.exists()
        
        # Verify database was updated
        test_db_file_session.refresh(test_player)
        assert test_player.thumbnail_image is None

    def test_delete_player_portrait_no_portrait(self, isolated_client, auth_headers, test_player):
        """Test deleting portrait when player has no portrait."""
        response = isolated_client.delete(
            f"/v1/players/{test_player.id}/portrait",
            headers=auth_headers,
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"] == "NO_PORTRAIT_TO_DELETE"

    def test_delete_player_portrait_unauthorized(self, isolated_unauthenticated_client, test_player):
        """Test portrait deletion without authentication."""
        response = isolated_unauthenticated_client.delete(f"/v1/players/{test_player.id}/portrait")
        
        assert response.status_code == 401

    def test_player_detail_page_shows_portrait(self, isolated_client, auth_headers, test_player):
        """Test that player detail page shows uploaded portrait."""
        # Upload a portrait
        image_data = self.create_test_image()
        upload_response = isolated_client.post(
            f"/v1/players/{test_player.id}/portrait",
            files={"file": ("portrait.jpg", image_data, "image/jpeg")},
            headers=auth_headers,
        )
        assert upload_response.status_code == 200
        
        # Get player stats which includes portrait info
        stats_response = isolated_client.get(f"/v1/players/{test_player.id}/stats")
        assert stats_response.status_code == 200
        
        stats_data = stats_response.json()
        assert stats_data["player"]["thumbnail_image"] is not None
        assert f"players/{test_player.id}/portrait.jpg" in stats_data["player"]["thumbnail_image"]

    def test_legacy_upload_endpoint_compatibility(self, isolated_client, auth_headers, test_player, test_db_file_session):
        """Test that legacy upload-image endpoint still works."""
        image_data = self.create_test_image()
        
        # Use legacy endpoint
        response = isolated_client.post(
            f"/v1/players/{test_player.id}/upload-image",
            files={"file": ("portrait.jpg", image_data, "image/jpeg")},
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # Verify portrait was uploaded
        test_db_file_session.refresh(test_player)
        assert test_player.thumbnail_image is not None

    def test_portrait_url_template_helper(self, isolated_client, test_player, test_db_file_session):
        """Test that portrait URL is correctly generated in templates."""
        from app.web_ui.templates_config import player_portrait_url
        
        # Clean up any existing portrait files and database records first
        test_player.thumbnail_image = None
        test_db_file_session.commit()
        
        # Clean up any existing files
        portrait_dir = ImageProcessingService.get_image_directory(
            test_player.id,
            ImageType.PLAYER_PORTRAIT
        )
        if portrait_dir.exists():
            import shutil
            shutil.rmtree(portrait_dir)
        
        # Clear cache
        from app.web_ui.templates_config import clear_player_portrait_cache
        clear_player_portrait_cache()
        
        # Test with no portrait
        url = player_portrait_url(test_player)
        assert url is None
        
        # Upload portrait
        image_data = self.create_test_image()
        # Simulate portrait upload by updating database
        test_player.thumbnail_image = f"players/{test_player.id}/portrait.jpg"
        test_db_file_session.add(test_player)
        test_db_file_session.commit()
        
        # Create the actual file
        portrait_dir = ImageProcessingService.get_image_directory(
            test_player.id,
            ImageType.PLAYER_PORTRAIT
        )
        portrait_dir.mkdir(parents=True, exist_ok=True)
        portrait_path = portrait_dir / "portrait.jpg"
        
        img = Image.new("RGB", (200, 200), color="blue")
        img.save(portrait_path, "JPEG")
        
        # Clear cache to get fresh data
        from app.web_ui.templates_config import clear_player_portrait_cache
        clear_player_portrait_cache()
        
        # Test portrait URL generation - refresh player from database to get real object
        test_db_file_session.refresh(test_player)
        url = player_portrait_url(test_player)
        assert url is not None
        assert f"/uploads/players/{test_player.id}/portrait.jpg" in url