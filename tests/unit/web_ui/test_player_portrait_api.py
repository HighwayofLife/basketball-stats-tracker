"""Unit tests for player portrait API endpoints."""

import io
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException
from PIL import Image
from sqlalchemy.orm import Session

from app.auth.models import User
from app.data_access import models
from app.services.image_processing_service import ImageProcessingService
from app.web_ui.routers.players import delete_player_portrait, upload_player_portrait


class TestPlayerPortraitAPI:
    """Test cases for player portrait API endpoints."""

    @pytest.mark.asyncio
    async def test_upload_player_portrait_success(self):
        """Test successful player portrait upload."""
        player_id = 123

        # Create mock objects
        mock_file = Mock()
        mock_file.filename = "portrait.jpg"
        mock_file.content_type = "image/jpeg"

        mock_user = Mock(spec=User)
        mock_user.id = 1

        # Create a valid test image
        img = Image.new("RGB", (200, 200), color="blue")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG")
        img_bytes.seek(0)
        mock_file.read = AsyncMock(return_value=img_bytes.getvalue())

        # Create a mock session
        mock_session = Mock(spec=Session)

        # Mock the player query
        mock_player = Mock(spec=models.Player)
        mock_player.id = player_id
        mock_player.name = "Test Player"
        mock_player.thumbnail_image = None

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_player
        mock_session.query.return_value = mock_query

        # Mock the image processing service
        with patch.object(ImageProcessingService, "process_player_portrait") as mock_process:
            mock_process.return_value = "/uploads/players/123/portrait.jpg"

            with patch.object(ImageProcessingService, "update_player_portrait_filename") as mock_update:
                mock_update.return_value = "players/123/portrait.jpg"

                with patch("app.web_ui.templates_config.clear_player_portrait_cache"):
                    # Call the endpoint with session parameter
                    result = await upload_player_portrait(
                        player_id=player_id,
                        file=mock_file,
                        current_user=mock_user,
                        session=mock_session
                    )

                # Verify results
                assert result["success"] is True
                assert result["portrait_url"] == "/uploads/players/123/portrait.jpg"
                assert result["player_id"] == 123
                assert result["filename"] == "players/123/portrait.jpg"

                # Verify the player's thumbnail_image was updated
                assert mock_player.thumbnail_image == "players/123/portrait.jpg"

                # Verify database commit was called
                mock_session.commit.assert_called_once()

                # Verify image processing was called
                mock_process.assert_called_once_with(player_id, mock_file)
                mock_update.assert_called_once_with(player_id)

    @pytest.mark.asyncio
    async def test_upload_player_portrait_player_not_found(self):
        """Test portrait upload when player doesn't exist."""
        player_id = 999

        mock_file = Mock()
        mock_file.filename = "portrait.jpg"
        mock_file.content_type = "image/jpeg"

        mock_user = Mock(spec=User)
        mock_user.id = 1

        # Create a mock session
        mock_session = Mock(spec=Session)

        # Mock the player query to return None
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_session.query.return_value = mock_query

        # Call the endpoint and expect an exception
        with pytest.raises(HTTPException) as exc_info:
            await upload_player_portrait(
                player_id=player_id,
                file=mock_file,
                current_user=mock_user,
                session=mock_session
            )

            assert exc_info.value.status_code == 404
            assert exc_info.value.detail["error"] == "PLAYER_NOT_FOUND"
            assert "Player with ID 999 not found" in exc_info.value.detail["message"]

    @pytest.mark.asyncio
    async def test_upload_player_portrait_processing_error(self):
        """Test portrait upload when image processing fails."""
        player_id = 123

        mock_file = Mock()
        mock_file.filename = "portrait.jpg"
        mock_file.content_type = "image/jpeg"

        mock_user = Mock(spec=User)
        mock_user.id = 1

        # Create a mock session
        mock_session = Mock(spec=Session)

        # Mock the player query
        mock_player = Mock(spec=models.Player)
        mock_player.id = player_id
        mock_player.name = "Test Player"

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_player
        mock_session.query.return_value = mock_query

        # Mock the image processing service to raise an error
        with patch.object(ImageProcessingService, "process_player_portrait") as mock_process:
            mock_process.side_effect = Exception("Processing failed")

            # Call the endpoint and expect an exception
            with pytest.raises(HTTPException) as exc_info:
                await upload_player_portrait(
                    player_id=player_id,
                    file=mock_file,
                    current_user=mock_user,
                    session=mock_session
                )

                assert exc_info.value.status_code == 500
                assert exc_info.value.detail["error"] == "UPLOAD_FAILED"
                assert "unexpected error" in exc_info.value.detail["message"]

    @pytest.mark.asyncio
    async def test_delete_player_portrait_success(self):
        """Test successful player portrait deletion."""
        player_id = 123

        mock_user = Mock(spec=User)
        mock_user.id = 1

        # Create a mock session
        mock_session = Mock(spec=Session)

        # Mock the player query
        mock_player = Mock(spec=models.Player)
        mock_player.id = player_id
        mock_player.name = "Test Player"
        mock_player.thumbnail_image = "players/123/portrait.jpg"

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_player
        mock_session.query.return_value = mock_query

        # Mock the image processing service
        with patch.object(ImageProcessingService, "delete_player_portrait") as mock_delete:
            with patch("app.web_ui.templates_config.clear_player_portrait_cache"):
                # Call the endpoint
                result = await delete_player_portrait(
                    player_id=player_id,
                    current_user=mock_user,
                    session=mock_session
                )

                # Verify results
                assert result["success"] is True
                assert result["message"] == "Portrait deleted successfully"
                assert result["player_id"] == 123
                assert result["deleted_filename"] == "players/123/portrait.jpg"

                # Verify the player's thumbnail_image was cleared
                assert mock_player.thumbnail_image is None

                # Verify database commit was called
                mock_session.commit.assert_called_once()

                # Verify image deletion was called
                mock_delete.assert_called_once_with(player_id)

    @pytest.mark.asyncio
    async def test_delete_player_portrait_player_not_found(self):
        """Test portrait deletion when player doesn't exist."""
        player_id = 999

        mock_user = Mock(spec=User)
        mock_user.id = 1

        # Create a mock session
        mock_session = Mock(spec=Session)

        # Mock the player query to return None
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_session.query.return_value = mock_query

        # Call the endpoint and expect an exception
        with pytest.raises(HTTPException) as exc_info:
            await delete_player_portrait(
                player_id=player_id,
                current_user=mock_user,
                session=mock_session
            )

            assert exc_info.value.status_code == 404
            assert exc_info.value.detail["error"] == "PLAYER_NOT_FOUND"
            assert "Player with ID 999 not found" in exc_info.value.detail["message"]

    @pytest.mark.asyncio
    async def test_delete_player_portrait_no_portrait(self):
        """Test portrait deletion when player has no portrait."""
        player_id = 123

        mock_user = Mock(spec=User)
        mock_user.id = 1

        # Create a mock session
        mock_session = Mock(spec=Session)

        # Mock the player query
        mock_player = Mock(spec=models.Player)
        mock_player.id = player_id
        mock_player.name = "Test Player"
        mock_player.thumbnail_image = None  # No portrait

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_player
        mock_session.query.return_value = mock_query

        # Call the endpoint and expect an exception
        with pytest.raises(HTTPException) as exc_info:
            await delete_player_portrait(
                player_id=player_id,
                current_user=mock_user,
                session=mock_session
            )

            assert exc_info.value.status_code == 404
            assert exc_info.value.detail["error"] == "PORTRAIT_NOT_FOUND"
            assert "does not have a portrait" in exc_info.value.detail["message"]

    @pytest.mark.asyncio
    async def test_delete_player_portrait_deletion_error(self):
        """Test portrait deletion when file deletion fails."""
        player_id = 123

        mock_user = Mock(spec=User)
        mock_user.id = 1

        # Create a mock session
        mock_session = Mock(spec=Session)

        # Mock the player query
        mock_player = Mock(spec=models.Player)
        mock_player.id = player_id
        mock_player.name = "Test Player"
        mock_player.thumbnail_image = "players/123/portrait.jpg"

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_player
        mock_session.query.return_value = mock_query

        # Mock the image processing service to raise an error
        with patch.object(ImageProcessingService, "delete_player_portrait") as mock_delete:
            mock_delete.side_effect = Exception("Deletion failed")

            with patch("app.web_ui.templates_config.clear_player_portrait_cache"):
                # Call the endpoint and expect an exception
                with pytest.raises(HTTPException) as exc_info:
                    await delete_player_portrait(
                        player_id=player_id,
                        current_user=mock_user,
                        session=mock_session
                    )

                assert exc_info.value.status_code == 500
                assert exc_info.value.detail["error"] == "FILE_DELETE_ERROR"
                assert "Failed to delete portrait files" in exc_info.value.detail["message"]
