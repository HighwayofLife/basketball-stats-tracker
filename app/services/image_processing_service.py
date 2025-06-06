"""Image processing service for team logos and other image uploads."""

import contextlib
import io
import logging
import os
import shutil
from pathlib import Path

from fastapi import HTTPException, UploadFile
from PIL import Image

from app.config import TEAM_LOGO_MAX_HEIGHT, TEAM_LOGO_MAX_WIDTH, TEAM_LOGOS_SUBDIR, UPLOADS_URL_PREFIX, settings

logger = logging.getLogger(__name__)

UPLOADS_DIR = Path(settings.UPLOAD_DIR)


class ImageProcessingService:
    """Service for processing and storing team logo images."""

    # Maximum dimensions for team logos (preserves aspect ratio)
    MAX_LOGO_DIMENSIONS = (TEAM_LOGO_MAX_WIDTH, TEAM_LOGO_MAX_HEIGHT)

    # Supported image formats
    SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".webp"}
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

    @staticmethod
    def validate_image_file(file: UploadFile, contents: bytes) -> None:
        """Validate image file type, size, and format."""
        # Check MIME type
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image file.")

        # Check file size
        if len(contents) > ImageProcessingService.MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large. Maximum size is 5MB.")

        # Check file extension
        file_extension = os.path.splitext(file.filename or "")[1].lower()
        if file_extension not in ImageProcessingService.SUPPORTED_FORMATS:
            formats = ", ".join(ImageProcessingService.SUPPORTED_FORMATS)
            raise HTTPException(status_code=400, detail=f"Invalid file format. Supported formats: {formats}.")

        # Validate that it's actually an image by trying to open it
        try:
            with Image.open(io.BytesIO(contents)) as img:
                img.verify()
        except Exception as e:
            logger.error(f"Image validation failed: {e}")
            raise HTTPException(status_code=400, detail="Invalid image file.") from e

    @staticmethod
    def resize_image_to_fit(image: Image.Image, max_width: int, max_height: int) -> Image.Image:
        """Resize an image to fit within max dimensions while maintaining aspect ratio."""
        original_width, original_height = image.size

        # If image is already smaller than max dimensions, return as-is
        if original_width <= max_width and original_height <= max_height:
            return image

        # Calculate scaling factor to fit within max dimensions
        width_ratio = max_width / original_width
        height_ratio = max_height / original_height

        # Use the smaller ratio to ensure image fits within both dimensions
        scale_factor = min(width_ratio, height_ratio)

        # Calculate new dimensions
        new_width = int(original_width * scale_factor)
        new_height = int(original_height * scale_factor)

        # Resize the image maintaining aspect ratio
        resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        return resized_image

    @staticmethod
    def get_team_logo_directory(team_id: int) -> Path:
        """Get the directory path for a team's logo files."""
        return Path(settings.UPLOAD_DIR) / TEAM_LOGOS_SUBDIR / str(team_id)

    @staticmethod
    def get_team_logo_path(team_id: int, filename: str) -> Path:
        """Get the full path for a team logo file."""
        team_dir = ImageProcessingService.get_team_logo_directory(team_id)
        return team_dir / filename

    @staticmethod
    def get_team_logo_url(team_id: int) -> str | None:
        """Get the URL for a team logo."""
        team_dir = ImageProcessingService.get_team_logo_directory(team_id)

        if not team_dir.exists():
            return None

        # Look for any supported image file
        for file_path in team_dir.iterdir():
            if file_path.suffix.lower() in ImageProcessingService.SUPPORTED_FORMATS:
                # Always use uploads endpoint since uploads are outside app directory
                try:
                    relative_path = file_path.relative_to(UPLOADS_DIR)
                    return f"{UPLOADS_URL_PREFIX}{relative_path}"
                except ValueError:
                    # Fallback for tests or edge cases
                    return f"{UPLOADS_URL_PREFIX}{TEAM_LOGOS_SUBDIR}/{team_id}/{file_path.name}"

        return None

    @staticmethod
    def delete_team_logo(team_id: int) -> None:
        """Delete all logo files for a team."""
        team_dir = ImageProcessingService.get_team_logo_directory(team_id)

        if team_dir.exists():
            try:
                logger.info(f"Attempting to delete logo directory for team {team_id}: {team_dir}")
                shutil.rmtree(team_dir)
                logger.info(f"Successfully deleted logo directory for team {team_id}")
            except Exception as e:
                logger.error(f"Error deleting logo directory for team {team_id}: {e}")
                raise HTTPException(status_code=500, detail="Failed to delete logo files") from e
        else:
            logger.info(f"Logo directory for team {team_id} does not exist: {team_dir}")

    @staticmethod
    async def process_team_logo(team_id: int, file: UploadFile) -> str:
        """
        Process and store a team logo.

        Args:
            team_id: The ID of the team
            file: The uploaded image file

        Returns:
            URL for the processed logo: "/uploads/teams/1/logo.jpg"
        """
        try:
            # Read file contents
            contents = await file.read()

            # Validate the file
            ImageProcessingService.validate_image_file(file, contents)

            # Create team directory
            team_dir = ImageProcessingService.get_team_logo_directory(team_id)

            # Clean up existing logo if it exists
            logger.info(f"Processing new logo for team {team_id}, checking for existing logos...")
            ImageProcessingService.delete_team_logo(team_id)

            # Create directory
            logger.info(f"Creating directory for team {team_id}")
            team_dir.mkdir(parents=True, exist_ok=True)

            # Determine output format and filename based on original file
            file_extension = os.path.splitext(file.filename or "")[1].lower()

            # Map file extensions to PIL format names
            format_mapping = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP"}

            output_format = format_mapping.get(file_extension, "JPEG")
            filename = f"logo{file_extension}" if file_extension else "logo.jpg"

            # Open and process the image
            with Image.open(io.BytesIO(contents)) as original_image:
                # Resize to fit within max dimensions while preserving aspect ratio
                max_width, max_height = ImageProcessingService.MAX_LOGO_DIMENSIONS
                processed_image = ImageProcessingService.resize_image_to_fit(original_image, max_width, max_height)

                # Save the processed image
                output_path = ImageProcessingService.get_team_logo_path(team_id, filename)

                # Handle different formats appropriately
                save_kwargs = {}
                if output_format == "JPEG":
                    # For JPEG, convert to RGB if necessary
                    if processed_image.mode != "RGB":
                        processed_image = processed_image.convert("RGB")
                    # Use high quality
                    save_kwargs["quality"] = 90
                    save_kwargs["optimize"] = True
                elif output_format == "PNG":
                    # PNG supports transparency
                    if processed_image.mode not in ("RGBA", "RGB"):
                        processed_image = processed_image.convert("RGBA")
                    # PNG compression level
                    save_kwargs["optimize"] = True
                elif output_format == "WEBP":
                    # Use high quality WebP
                    save_kwargs["quality"] = 90
                    save_kwargs["method"] = 6

                processed_image.save(output_path, output_format, **save_kwargs)

                # Generate URL - always use uploads endpoint
                try:
                    relative_path = output_path.relative_to(UPLOADS_DIR)
                    logo_url = f"{UPLOADS_URL_PREFIX}{relative_path}"
                except ValueError:
                    # Fallback for tests or edge cases
                    logo_url = f"{UPLOADS_URL_PREFIX}{TEAM_LOGOS_SUBDIR}/{team_id}/{filename}"

                logger.info(f"Successfully processed team logo for team {team_id}")
                return logo_url

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing team logo for team {team_id}: {e}")
            # Clean up any partial files on error
            with contextlib.suppress(Exception):
                ImageProcessingService.delete_team_logo(team_id)
            raise HTTPException(status_code=500, detail="Failed to process logo image") from e

    @staticmethod
    def update_team_logo_filename(team_id: int) -> str | None:
        """
        Update and return the logo filename for a team.
        This should be called after successful logo processing to update the database.

        Returns:
            The relative path to store in the database (e.g., "teams/1/logo.png") or None if no logo exists
        """
        logo_url = ImageProcessingService.get_team_logo_url(team_id)
        if logo_url and logo_url.startswith(UPLOADS_URL_PREFIX):
            # Remove uploads URL prefix for database storage
            return logo_url.removeprefix(UPLOADS_URL_PREFIX)

        # Fallback: look for any supported format in the team directory
        team_dir = ImageProcessingService.get_team_logo_directory(team_id)
        if team_dir.exists():
            for file_path in team_dir.iterdir():
                if file_path.suffix.lower() in ImageProcessingService.SUPPORTED_FORMATS:
                    return f"{TEAM_LOGOS_SUBDIR}/{team_id}/{file_path.name}"

        # No logo found
        return None
