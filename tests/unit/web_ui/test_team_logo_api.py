"""Unit tests for team logo API endpoints."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth.models import User
from app.config import UPLOADS_URL_PREFIX
from app.data_access.models import Team
from app.services.audit_log_service import AuditLogService
from app.services.image_processing_service import ImageProcessingService
from app.web_ui.routers.teams import delete_team_logo, upload_team_logo


class TestTeamLogoAPI:
    """Test cases for team logo API endpoints."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def mock_user(self):
        """Mock authenticated user."""
        user = Mock(spec=User)
        user.id = 1
        user.username = "testuser"
        return user

    @pytest.fixture
    def mock_team(self):
        """Mock team object."""
        team = Mock(spec=Team)
        team.id = 1
        team.name = "Test Team"
        team.logo_filename = None
        return team

    @pytest.fixture
    def mock_image_file(self, test_image_blue):
        """Create a mock image upload file."""
        filename, img_bytes, content_type = test_image_blue

        file = Mock(spec=UploadFile)
        file.content_type = "image/jpeg"
        file.filename = "test.jpg"
        file.read = AsyncMock(return_value=img_bytes.getvalue())

        return file

    @pytest.mark.asyncio
    async def test_upload_team_logo_success(self, mock_db, mock_user, mock_team, mock_image_file):
        """Test successful team logo upload."""
        # Setup mocks
        mock_db.query.return_value.filter.return_value.first.return_value = mock_team

        mock_logo_url = f"{UPLOADS_URL_PREFIX}teams/1/logo.jpg"

        with patch.object(ImageProcessingService, "process_team_logo", new_callable=AsyncMock) as mock_process:
            mock_process.return_value = mock_logo_url

            with patch.object(ImageProcessingService, "update_team_logo_filename") as mock_update_filename:
                mock_update_filename.return_value = "teams/1/logo.jpg"

                with patch.object(AuditLogService, "__init__", return_value=None):
                    with patch.object(AuditLogService, "log_update") as mock_log:
                        result = await upload_team_logo(
                            team_id=1, file=mock_image_file, current_user=mock_user, db=mock_db
                        )

        # Assertions
        assert result["success"] is True
        assert result["message"] == "Logo uploaded successfully"
        assert result["logo_url"] == mock_logo_url
        assert result["logo_filename"] == "teams/1/logo.jpg"

        # Verify team logo filename was updated
        assert mock_team.logo_filename == "teams/1/logo.jpg"

        # Verify database commit was called
        mock_db.commit.assert_called_once()

        # Verify audit log was created
        mock_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_team_logo_team_not_found(self, mock_db, mock_user, mock_image_file):
        """Test team logo upload when team doesn't exist."""
        # Setup mock to return None (team not found)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await upload_team_logo(team_id=999, file=mock_image_file, current_user=mock_user, db=mock_db)

        assert exc_info.value.status_code == 404
        assert "Team not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_upload_team_logo_image_processing_error(self, mock_db, mock_user, mock_team, mock_image_file):
        """Test team logo upload when image processing fails."""
        # Setup mocks
        mock_db.query.return_value.filter.return_value.first.return_value = mock_team

        with patch.object(ImageProcessingService, "process_team_logo", new_callable=AsyncMock) as mock_process:
            mock_process.side_effect = HTTPException(status_code=400, detail="Invalid image file")

            with pytest.raises(HTTPException) as exc_info:
                await upload_team_logo(team_id=1, file=mock_image_file, current_user=mock_user, db=mock_db)

            assert exc_info.value.status_code == 400
            assert "Invalid image file" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_upload_team_logo_replaces_existing(self, mock_db, mock_user, mock_image_file):
        """Test that uploading a new logo replaces existing one."""
        # Setup team with existing logo
        mock_team = Mock(spec=Team)
        mock_team.id = 1
        mock_team.name = "Test Team"
        mock_team.logo_filename = "teams/1/old_logo.jpg"

        mock_db.query.return_value.filter.return_value.first.return_value = mock_team

        mock_logo_url = f"{UPLOADS_URL_PREFIX}teams/1/logo.jpg"

        with patch.object(ImageProcessingService, "process_team_logo", new_callable=AsyncMock) as mock_process:
            mock_process.return_value = mock_logo_url

            with patch.object(ImageProcessingService, "update_team_logo_filename") as mock_update_filename:
                mock_update_filename.return_value = "teams/1/logo.jpg"

                with patch.object(AuditLogService, "__init__", return_value=None):
                    with patch.object(AuditLogService, "log_update") as mock_log:
                        result = await upload_team_logo(
                            team_id=1, file=mock_image_file, current_user=mock_user, db=mock_db
                        )

        # Verify that audit log captured the old and new values
        mock_log.assert_called_once()
        call_args = mock_log.call_args
        assert call_args[1]["old_values"]["logo_filename"] == "teams/1/old_logo.jpg"
        assert call_args[1]["new_values"]["logo_filename"] == "teams/1/logo.jpg"

    @pytest.mark.asyncio
    async def test_delete_team_logo_success(self, mock_db, mock_user):
        """Test successful team logo deletion."""
        # Setup team with existing logo
        mock_team = Mock(spec=Team)
        mock_team.id = 1
        mock_team.name = "Test Team"
        mock_team.logo_filename = "teams/1/logo.jpg"

        mock_db.query.return_value.filter.return_value.first.return_value = mock_team

        with patch.object(ImageProcessingService, "delete_team_logo") as mock_delete:
            with patch.object(AuditLogService, "__init__", return_value=None):
                with patch.object(AuditLogService, "log_update") as mock_log:
                    result = await delete_team_logo(team_id=1, current_user=mock_user, db=mock_db)

        # Assertions
        assert result["success"] is True
        assert result["message"] == "Logo deleted successfully"
        assert result["deleted_logo"] == "teams/1/logo.jpg"

        # Verify team logo filename was cleared
        assert mock_team.logo_filename is None

        # Verify file deletion was called
        mock_delete.assert_called_once_with(1)

        # Verify database commit was called
        mock_db.commit.assert_called_once()

        # Verify audit log was created
        mock_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_team_logo_team_not_found(self, mock_db, mock_user):
        """Test team logo deletion when team doesn't exist."""
        # Setup mock to return None (team not found)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await delete_team_logo(team_id=999, current_user=mock_user, db=mock_db)

        assert exc_info.value.status_code == 404
        assert "Team not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_delete_team_logo_no_existing_logo(self, mock_db, mock_user):
        """Test team logo deletion when team has no logo."""
        # Setup team without logo
        mock_team = Mock(spec=Team)
        mock_team.id = 1
        mock_team.name = "Test Team"
        mock_team.logo_filename = None

        mock_db.query.return_value.filter.return_value.first.return_value = mock_team

        with pytest.raises(HTTPException) as exc_info:
            await delete_team_logo(team_id=1, current_user=mock_user, db=mock_db)

        assert exc_info.value.status_code == 400
        assert "Team has no logo to delete" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_delete_team_logo_filesystem_error(self, mock_db, mock_user):
        """Test team logo deletion when filesystem deletion fails."""
        # Setup team with existing logo
        mock_team = Mock(spec=Team)
        mock_team.id = 1
        mock_team.name = "Test Team"
        mock_team.logo_filename = "teams/1/logo.jpg"

        mock_db.query.return_value.filter.return_value.first.return_value = mock_team

        with patch.object(ImageProcessingService, "delete_team_logo") as mock_delete:
            mock_delete.side_effect = HTTPException(status_code=500, detail="Failed to delete logo files")

            with pytest.raises(HTTPException) as exc_info:
                await delete_team_logo(team_id=1, current_user=mock_user, db=mock_db)

            assert exc_info.value.status_code == 500
            assert "Failed to delete logo files" in exc_info.value.detail
