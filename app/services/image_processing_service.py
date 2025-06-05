"""Image processing service for team logos and other image uploads."""

import contextlib
import io
import logging
import os
import shutil
from pathlib import Path

from fastapi import HTTPException, UploadFile
from PIL import Image

from app.config import settings

logger = logging.getLogger(__name__)

UPLOADS_DIR = Path(settings.UPLOAD_DIR)
UPLOADS_URL_PREFIX = "/uploads/"


class ImageProcessingService:
    """Service for processing and storing team logo images with multiple sizes."""

    # Define the sizes we need for team logos
    LOGO_SIZES = {
        "original": None,  # Keep original size
        "120x120": (120, 120),  # Medium size for team detail page
        "64x64": (64, 64),  # Small size for games tables
    }

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
    def resize_and_crop_image(image: Image.Image, target_size: tuple[int, int]) -> Image.Image:
        """Resize an image to fit within target dimensions while maintaining aspect ratio."""
        # Calculate scaling factor to fit within target dimensions
        original_width, original_height = image.size
        target_width, target_height = target_size

        # Calculate aspect ratios
        original_ratio = original_width / original_height
        target_ratio = target_width / target_height

        # Determine scaling factor - scale to fit within the target dimensions
        if original_ratio > target_ratio:
            # Image is wider, scale by width
            scale_factor = target_width / original_width
        else:
            # Image is taller, scale by height
            scale_factor = target_height / original_height

        # Calculate new dimensions
        new_width = int(original_width * scale_factor)
        new_height = int(original_height * scale_factor)

        # Resize the image maintaining aspect ratio
        resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        return resized_image

    @staticmethod
    def get_team_logo_directory(team_id: int) -> Path:
        """Get the directory path for a team's logo files."""
        return Path(settings.UPLOAD_DIR) / "teams" / str(team_id)

    @staticmethod
    def get_team_logo_path(team_id: int, size: str, filename: str) -> Path:
        """Get the full path for a team logo file of a specific size."""
        team_dir = ImageProcessingService.get_team_logo_directory(team_id)
        return team_dir / size / filename

    @staticmethod
    def get_team_logo_url(team_id: int, size: str = "120x120") -> str | None:
        """Get the URL for a team logo of a specific size."""
        team_dir = ImageProcessingService.get_team_logo_directory(team_id)
        size_dir = team_dir / size

        if not size_dir.exists():
            return None

        # Look for any supported image file
        for file_path in size_dir.iterdir():
            if file_path.suffix.lower() in ImageProcessingService.SUPPORTED_FORMATS:
                # Always use uploads endpoint since uploads are outside app directory
                try:
                    relative_path = file_path.relative_to(UPLOADS_DIR)
                    return f"{UPLOADS_URL_PREFIX}{relative_path}"
                except ValueError:
                    # Fallback for tests or edge cases
                    return f"{UPLOADS_URL_PREFIX}teams/{team_id}/{size}/{file_path.name}"

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
    async def process_team_logo(team_id: int, file: UploadFile) -> dict[str, str]:
        """
        Process and store a team logo in multiple sizes.

        Args:
            team_id: The ID of the team
            file: The uploaded image file

        Returns:
            Dictionary with URLs for each size: {"120x120": "/uploads/teams/1/120x120/logo.jpg", ...}
        """
        try:
            # Read file contents
            contents = await file.read()

            # Validate the file
            ImageProcessingService.validate_image_file(file, contents)

            # Create team directory structure
            team_dir = ImageProcessingService.get_team_logo_directory(team_id)

            # Clean up existing logo if it exists
            logger.info(f"Processing new logo for team {team_id}, checking for existing logos...")
            ImageProcessingService.delete_team_logo(team_id)

            # Create new directory structure
            logger.info(f"Creating new directory structure for team {team_id}")
            for size in ImageProcessingService.LOGO_SIZES:
                size_dir = team_dir / size
                size_dir.mkdir(parents=True, exist_ok=True)

            # Determine output format and filename based on original file
            file_extension = os.path.splitext(file.filename or "")[1].lower()

            # Map file extensions to PIL format names
            format_mapping = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP"}

            output_format = format_mapping.get(file_extension, "JPEG")
            filename = f"logo{file_extension}" if file_extension else "logo.jpg"

            # Open the image
            with Image.open(io.BytesIO(contents)) as original_image:
                # Process each size
                urls = {}

                for size_name, dimensions in ImageProcessingService.LOGO_SIZES.items():
                    if size_name == "original":
                        # Save original as-is, preserving format
                        processed_image = original_image
                    else:
                        # Resize and crop to target dimensions
                        processed_image = ImageProcessingService.resize_and_crop_image(original_image, dimensions)

                    # Save the processed image
                    output_path = ImageProcessingService.get_team_logo_path(team_id, size_name, filename)

                    # Handle different formats appropriately
                    save_kwargs = {}
                    if output_format == "JPEG":
                        # For JPEG, convert to RGB if necessary
                        if processed_image.mode != "RGB":
                            processed_image = processed_image.convert("RGB")
                        # Use maximum quality (95-100 is essentially lossless for JPEG)
                        save_kwargs["quality"] = 100
                        save_kwargs["subsampling"] = 0  # Disable chroma subsampling
                        save_kwargs["optimize"] = False  # Don't optimize to maintain quality
                    elif output_format == "PNG":
                        # PNG supports transparency
                        if processed_image.mode not in ("RGBA", "RGB"):
                            processed_image = processed_image.convert("RGBA")
                        # PNG is lossless by default, but ensure no compression
                        save_kwargs["compress_level"] = 0  # No compression
                    elif output_format == "WEBP":
                        # Use lossless WebP
                        save_kwargs["lossless"] = True
                        save_kwargs["quality"] = 100  # Ignored in lossless mode
                        save_kwargs["method"] = 6  # Highest quality method

                    processed_image.save(output_path, output_format, **save_kwargs)

                    # Generate URL - always use uploads endpoint
                    try:
                        relative_path = output_path.relative_to(UPLOADS_DIR)
                        urls[size_name] = f"{UPLOADS_URL_PREFIX}{relative_path}"
                    except ValueError:
                        # Fallback for tests or edge cases
                        urls[size_name] = f"{UPLOADS_URL_PREFIX}teams/{team_id}/{size_name}/{filename}"

                logger.info(f"Successfully processed team logo for team {team_id}")
                return urls

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing team logo for team {team_id}: {e}")
            # Clean up any partial files on error
            with contextlib.suppress(Exception):
                ImageProcessingService.delete_team_logo(team_id)
            raise HTTPException(status_code=500, detail="Failed to process logo image") from e

    @staticmethod
    def update_team_logo_filename(team_id: int) -> str:
        """
        Update and return the logo filename for a team.
        This should be called after successful logo processing to update the database.

        Returns:
            The relative path to store in the database (e.g., "uploads/teams/1/120x120/logo.jpg")
        """
        logo_url = ImageProcessingService.get_team_logo_url(team_id, "120x120")
        if logo_url and logo_url.startswith("/uploads/"):
            # Remove /uploads/ prefix for database storage
            return logo_url.removeprefix("/uploads/")
        return f"teams/{team_id}/120x120/logo.jpg"
        return f"teams/{team_id}/120x120/logo.jpg"
