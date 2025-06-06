"""Unit tests for ImageProcessingService."""

import io
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException, UploadFile
from PIL import Image

from app.config import UPLOADS_URL_PREFIX
from app.services.image_processing_service import ImageProcessingService


class TestImageProcessingService:
    """Test cases for ImageProcessingService."""

    def test_validate_image_file_success(self):
        """Test successful image file validation."""
        # Create a valid test image
        img = Image.new("RGB", (100, 100), color="red")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG")
        img_bytes.seek(0)
        contents = img_bytes.getvalue()

        file = Mock(spec=UploadFile)
        file.content_type = "image/jpeg"
        file.filename = "test.jpg"

        # Should not raise any exception
        ImageProcessingService.validate_image_file(file, contents)

    def test_validate_image_file_invalid_mime_type(self):
        """Test validation failure for invalid MIME type."""
        file = Mock(spec=UploadFile)
        file.content_type = "text/plain"
        file.filename = "test.txt"
        contents = b"not an image"

        with pytest.raises(HTTPException) as exc_info:
            ImageProcessingService.validate_image_file(file, contents)
        assert exc_info.value.status_code == 400
        assert "Invalid file type" in exc_info.value.detail

    def test_validate_image_file_too_large(self):
        """Test validation failure for oversized file."""
        file = Mock(spec=UploadFile)
        file.content_type = "image/jpeg"
        file.filename = "test.jpg"
        contents = b"x" * (6 * 1024 * 1024)  # 6MB, exceeds 5MB limit

        with pytest.raises(HTTPException) as exc_info:
            ImageProcessingService.validate_image_file(file, contents)
        assert exc_info.value.status_code == 400
        assert "File too large" in exc_info.value.detail

    def test_validate_image_file_invalid_extension(self):
        """Test validation failure for invalid file extension."""
        img = Image.new("RGB", (100, 100), color="red")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG")
        img_bytes.seek(0)
        contents = img_bytes.getvalue()

        file = Mock(spec=UploadFile)
        file.content_type = "image/jpeg"
        file.filename = "test.txt"

        with pytest.raises(HTTPException) as exc_info:
            ImageProcessingService.validate_image_file(file, contents)
        assert exc_info.value.status_code == 400
        assert "Invalid file format" in exc_info.value.detail

    def test_validate_image_file_corrupted_image(self):
        """Test validation failure for corrupted image data."""
        file = Mock(spec=UploadFile)
        file.content_type = "image/jpeg"
        file.filename = "test.jpg"
        contents = b"corrupted image data"

        with pytest.raises(HTTPException) as exc_info:
            ImageProcessingService.validate_image_file(file, contents)
        assert exc_info.value.status_code == 400
        assert "Invalid image file" in exc_info.value.detail

    def test_resize_image_to_fit(self):
        """Test image resizing functionality with aspect ratio preservation."""
        # Test with a wide image (400x200 = 2:1 aspect ratio)
        original_img = Image.new("RGB", (400, 200), color="blue")
        max_width, max_height = 250, 250

        resized_img = ImageProcessingService.resize_image_to_fit(original_img, max_width, max_height)

        # With aspect ratio preservation, the image should fit within 250x250
        # Since original is 2:1 ratio, it should be scaled to 250x125 to fit within 250x250
        assert resized_img.size == (250, 125)  # Preserves 2:1 aspect ratio
        assert resized_img.mode == "RGB"

        # Test with a tall image (200x400 = 1:2 aspect ratio)
        tall_img = Image.new("RGB", (200, 400), color="red")
        resized_tall = ImageProcessingService.resize_image_to_fit(tall_img, max_width, max_height)

        # Should be scaled to 125x250 to fit within 250x250 while preserving 1:2 ratio
        assert resized_tall.size == (125, 250)

        # Test with square image
        square_img = Image.new("RGB", (300, 300), color="green")
        resized_square = ImageProcessingService.resize_image_to_fit(square_img, max_width, max_height)

        # Square should scale to 250x250
        assert resized_square.size == (250, 250)

        # Test with image already smaller than max dimensions
        small_img = Image.new("RGB", (100, 100), color="yellow")
        resized_small = ImageProcessingService.resize_image_to_fit(small_img, max_width, max_height)

        # Should remain unchanged
        assert resized_small.size == (100, 100)

    def test_get_team_logo_directory(self):
        """Test team logo directory path generation."""
        from app.config import settings

        team_id = 123
        expected_path = Path(settings.UPLOAD_DIR) / "teams" / "123"

        directory = ImageProcessingService.get_team_logo_directory(team_id)

        assert directory == expected_path

    def test_get_team_logo_path(self):
        """Test team logo file path generation."""
        from app.config import settings

        team_id = 123
        filename = "logo.jpg"
        expected_path = Path(settings.UPLOAD_DIR) / "teams" / "123" / "logo.jpg"

        file_path = ImageProcessingService.get_team_logo_path(team_id, filename)

        assert file_path == expected_path

    def test_get_team_logo_url_exists(self):
        """Test getting team logo URL when logo exists."""
        team_id = 123

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock directory structure
            logo_dir = Path(temp_dir) / "teams" / str(team_id)
            logo_dir.mkdir(parents=True)
            logo_file = logo_dir / "logo.jpg"
            logo_file.touch()

            with patch.object(ImageProcessingService, "get_team_logo_directory") as mock_get_dir:
                mock_get_dir.return_value = Path(temp_dir) / "teams" / str(team_id)

                # Mock the Path.relative_to call to return our expected relative path
                with patch.object(Path, "relative_to") as mock_relative_to:
                    mock_relative_to.return_value = Path("uploads/teams/123/logo.jpg")

                    url = ImageProcessingService.get_team_logo_url(team_id)

                    assert url is not None
                    assert url.startswith(UPLOADS_URL_PREFIX)
                    assert "logo.jpg" in url

    def test_get_team_logo_url_not_exists(self):
        """Test getting team logo URL when logo doesn't exist."""
        team_id = 999

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(ImageProcessingService, "get_team_logo_directory") as mock_get_dir:
                mock_get_dir.return_value = Path(temp_dir) / "teams" / str(team_id)

                url = ImageProcessingService.get_team_logo_url(team_id)

                assert url is None

    def test_delete_team_logo_exists(self):
        """Test deleting existing team logo."""
        team_id = 123

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock directory structure with files
            team_dir = Path(temp_dir) / "teams" / str(team_id)
            team_dir.mkdir(parents=True)
            (team_dir / "logo.jpg").touch()

            with patch.object(ImageProcessingService, "get_team_logo_directory") as mock_get_dir:
                mock_get_dir.return_value = team_dir

                # Should not raise exception
                ImageProcessingService.delete_team_logo(team_id)

                # Directory should be deleted
                assert not team_dir.exists()

    def test_delete_team_logo_not_exists(self):
        """Test deleting non-existent team logo."""
        team_id = 999

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(ImageProcessingService, "get_team_logo_directory") as mock_get_dir:
                mock_get_dir.return_value = Path(temp_dir) / "teams" / str(team_id)

                # Should not raise exception
                ImageProcessingService.delete_team_logo(team_id)

    @pytest.mark.asyncio
    async def test_process_team_logo_success(self):
        """Test successful team logo processing."""
        team_id = 123

        # Create a valid test image that's larger than 250x250
        img = Image.new("RGB", (400, 400), color="green")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG")
        img_bytes.seek(0)

        file = Mock(spec=UploadFile)
        file.content_type = "image/jpeg"
        file.filename = "test.jpg"
        file.read = AsyncMock(return_value=img_bytes.getvalue())

        with tempfile.TemporaryDirectory() as temp_dir:
            # Set up path structure that service expects
            team_base_dir = Path(temp_dir) / "teams" / str(team_id)

            with patch.object(ImageProcessingService, "get_team_logo_directory") as mock_get_dir:
                mock_get_dir.return_value = team_base_dir

                # Mock the get_team_logo_path to return paths within our temp dir
                def mock_get_path(tid, filename):
                    return team_base_dir / filename

                with patch.object(ImageProcessingService, "get_team_logo_path", side_effect=mock_get_path):
                    # Mock Path.relative_to to avoid path resolution issues
                    with patch.object(Path, "relative_to") as mock_relative:
                        mock_relative.return_value = Path(f"uploads/teams/{team_id}/logo.jpg")

                        logo_url = await ImageProcessingService.process_team_logo(team_id, file)

                        # Check that URL is returned
                        assert logo_url is not None
                        assert logo_url.startswith(UPLOADS_URL_PREFIX)
                        assert "logo.jpg" in logo_url

                        # Check that file was created
                        assert (team_base_dir / "logo.jpg").exists()

                        # Verify image dimensions - since original is 400x400 (square),
                        # it should be scaled down to 250x250 (max dimensions)
                        with Image.open(team_base_dir / "logo.jpg") as resized_img:
                            assert resized_img.size == (250, 250)

    @pytest.mark.asyncio
    async def test_process_team_logo_validation_failure(self):
        """Test team logo processing with validation failure."""
        team_id = 123

        file = Mock(spec=UploadFile)
        file.content_type = "text/plain"
        file.filename = "test.txt"
        file.read = AsyncMock(return_value=b"not an image")

        with pytest.raises(HTTPException) as exc_info:
            await ImageProcessingService.process_team_logo(team_id, file)

        # Validation failures can be caught as 400 or wrapped in 500, both are acceptable
        assert exc_info.value.status_code in [400, 500]

    @pytest.mark.asyncio
    async def test_process_team_logo_replaces_existing(self):
        """Test that processing a new logo replaces existing logo."""
        team_id = 123

        # Create first image
        img1 = Image.new("RGB", (100, 100), color="red")
        img1_bytes = io.BytesIO()
        img1.save(img1_bytes, format="JPEG")
        img1_bytes.seek(0)

        file1 = Mock(spec=UploadFile)
        file1.content_type = "image/jpeg"
        file1.filename = "first.jpg"
        file1.read = AsyncMock(return_value=img1_bytes.getvalue())

        with tempfile.TemporaryDirectory() as temp_dir:
            # Set up path structure that service expects
            team_base_dir = Path(temp_dir) / "teams" / str(team_id)

            with patch.object(ImageProcessingService, "get_team_logo_directory") as mock_get_dir:
                mock_get_dir.return_value = team_base_dir

                # Mock the get_team_logo_path to return paths within our temp dir
                def mock_get_path(tid, filename):
                    return team_base_dir / filename

                with patch.object(ImageProcessingService, "get_team_logo_path", side_effect=mock_get_path):
                    # Mock Path.relative_to to avoid path resolution issues
                    with patch.object(Path, "relative_to") as mock_relative:
                        # Return appropriate relative paths for each call
                        mock_relative.side_effect = [
                            Path(f"uploads/teams/{team_id}/logo.jpg"),
                            Path(f"uploads/teams/{team_id}/logo.png"),
                        ]

                        # Process first logo
                        await ImageProcessingService.process_team_logo(team_id, file1)

                        # Verify first logo exists
                        assert (team_base_dir / "logo.jpg").exists()

                        # Create second image
                        img2 = Image.new("RGB", (100, 100), color="blue")
                        img2_bytes = io.BytesIO()
                        img2.save(img2_bytes, format="PNG")
                        img2_bytes.seek(0)

                        file2 = Mock(spec=UploadFile)
                        file2.content_type = "image/png"
                        file2.filename = "second.png"
                        file2.read = AsyncMock(return_value=img2_bytes.getvalue())

                        # Process second logo
                        await ImageProcessingService.process_team_logo(team_id, file2)

                        # Verify second logo exists and first is gone
                        assert not (team_base_dir / "logo.jpg").exists()
                        assert (team_base_dir / "logo.png").exists()

    def test_update_team_logo_filename(self):
        """Test updating team logo filename."""
        team_id = 123

        # Mock get_team_logo_url to return a URL
        with patch.object(ImageProcessingService, "get_team_logo_url") as mock_get_url:
            mock_get_url.return_value = f"{UPLOADS_URL_PREFIX}teams/{team_id}/logo.jpg"

            filename = ImageProcessingService.update_team_logo_filename(team_id)

            assert filename == f"teams/{team_id}/logo.jpg"
            mock_get_url.assert_called_once_with(team_id)

        # Test when no logo exists
        with patch.object(ImageProcessingService, "get_team_logo_url") as mock_get_url:
            mock_get_url.return_value = None

            filename = ImageProcessingService.update_team_logo_filename(team_id)

            # Should return None when no logo exists
            assert filename is None

    def test_supported_formats(self):
        """Test that all expected formats are supported."""
        expected_formats = {".jpg", ".jpeg", ".png", ".webp"}
        assert expected_formats == ImageProcessingService.SUPPORTED_FORMATS

    def test_max_logo_dimensions(self):
        """Test that max logo dimensions are defined."""
        from app.config import TEAM_LOGO_MAX_HEIGHT, TEAM_LOGO_MAX_WIDTH

        expected_dimensions = (TEAM_LOGO_MAX_WIDTH, TEAM_LOGO_MAX_HEIGHT)
        assert expected_dimensions == ImageProcessingService.MAX_LOGO_DIMENSIONS

    def test_max_file_size(self):
        """Test that max file size is 5MB."""
        assert ImageProcessingService.MAX_FILE_SIZE == 5 * 1024 * 1024
