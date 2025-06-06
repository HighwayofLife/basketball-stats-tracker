"""
Integration tests for team logo upload that run in the actual container environment.
These tests do NOT mock the upload directory and test against the real /data/uploads path.
"""

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import settings
from app.data_access.models import Team


class TestTeamLogoContainerEnvironment:
    """Integration tests that run against the actual container upload directory."""

    @pytest.fixture
    def client(self, test_db_file_session):
        """Create a FastAPI test client with isolated database."""
        from app.auth.dependencies import get_current_user, require_admin
        from app.auth.models import User, UserRole
        from app.web_ui.api import app
        from app.web_ui.dependencies import get_db

        def override_get_db():
            return test_db_file_session

        def mock_current_user():
            return User(
                id=1,
                username="testuser",
                email="test@example.com",
                role=UserRole.ADMIN,
                is_active=True,
                provider="local"
            )

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = mock_current_user
        app.dependency_overrides[require_admin] = mock_current_user
        client = TestClient(app)
        yield client
        app.dependency_overrides.clear()

    @pytest.fixture
    def test_team(self, test_db_file_session):
        """Create a test team."""
        team = Team(name="Container Test Team", display_name="Container Test Team")
        test_db_file_session.add(team)
        test_db_file_session.commit()
        test_db_file_session.refresh(team)
        return team

    @pytest.fixture
    def valid_image_file(self):
        """Create a valid image file for testing."""
        img = Image.new("RGB", (100, 100), color="blue")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG")
        img_bytes.seek(0)
        return ("test.jpg", img_bytes, "image/jpeg")

    @pytest.mark.skipif(
        not settings.UPLOAD_DIR.startswith("/data/"),
        reason="This test only runs in container environment with /data/uploads"
    )
    def test_upload_team_logo_real_container_directory(self, client, test_team, valid_image_file):
        """Test team logo upload using the real container upload directory."""
        # This test specifically DOES NOT mock the upload directory
        # It tests against the actual /data/uploads path used in the container
        
        response = client.post(
            f"/v1/teams/{test_team.id}/logo",
            files={"file": valid_image_file}
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

        # Verify files were actually created in the real directory
        team_dir = Path(settings.UPLOAD_DIR) / "teams" / str(test_team.id)
        assert team_dir.exists()
        assert (team_dir / "original" / "logo.jpg").exists()
        assert (team_dir / "120x120" / "logo.jpg").exists()
        assert (team_dir / "64x64" / "logo.jpg").exists()

        # Verify image dimensions
        with Image.open(team_dir / "120x120" / "logo.jpg") as img:
            # Should be scaled to fit within 120x120 while maintaining aspect ratio
            assert max(img.size) <= 120

        with Image.open(team_dir / "64x64" / "logo.jpg") as img:
            # Should be scaled to fit within 64x64 while maintaining aspect ratio
            assert max(img.size) <= 64

        # Clean up - delete the uploaded files
        import shutil
        if team_dir.exists():
            shutil.rmtree(team_dir)

    @pytest.mark.skipif(
        not settings.UPLOAD_DIR.startswith("/data/"),
        reason="This test only runs in container environment with /data/uploads"
    )
    def test_delete_team_logo_real_container_directory(self, client, test_team, valid_image_file):
        """Test team logo deletion using the real container upload directory."""
        # First upload a logo
        response = client.post(
            f"/v1/teams/{test_team.id}/logo",
            files={"file": valid_image_file}
        )
        assert response.status_code == 200

        # Verify files exist
        team_dir = Path(settings.UPLOAD_DIR) / "teams" / str(test_team.id)
        assert team_dir.exists()

        # Delete the logo
        response = client.delete(f"/v1/teams/{test_team.id}/logo")

        # Check response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Logo deleted successfully"

        # Verify files were actually deleted from the real directory
        assert not team_dir.exists()

    @pytest.mark.skipif(
        not settings.UPLOAD_DIR.startswith("/data/"),
        reason="This test only runs in container environment with /data/uploads"
    )
    def test_upload_permissions_container_environment(self, client, test_team):
        """Test that upload permissions work correctly in container environment."""
        # This test verifies that the container permission fix works
        upload_dir = Path(settings.UPLOAD_DIR)
        
        # Should be able to create subdirectories
        test_subdir = upload_dir / "test_permissions"
        test_subdir.mkdir(exist_ok=True)
        
        # Should be able to create files
        test_file = test_subdir / "test.txt"
        test_file.write_text("test content")
        
        # Verify file was created
        assert test_file.exists()
        assert test_file.read_text() == "test content"
        
        # Clean up
        import shutil
        if test_subdir.exists():
            shutil.rmtree(test_subdir)