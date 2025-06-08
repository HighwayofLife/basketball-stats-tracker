"""Image processing service for team logos and player portraits."""

import contextlib
import io
import logging
import os
import shutil
from enum import Enum
from pathlib import Path

from fastapi import HTTPException, UploadFile
from PIL import Image

from app.config import TEAM_LOGO_MAX_HEIGHT, TEAM_LOGO_MAX_WIDTH, TEAM_LOGOS_SUBDIR, UPLOADS_URL_PREFIX, settings

logger = logging.getLogger(__name__)

UPLOADS_DIR = Path(settings.UPLOAD_DIR)
PLAYER_PORTRAITS_SUBDIR = "players"  # Subdirectory for player portraits

# Maximum dimensions for portraits (same as team logos)
PLAYER_PORTRAIT_MAX_WIDTH = 250
PLAYER_PORTRAIT_MAX_HEIGHT = 250


class ImageType(Enum):
    """Enum for different types of images."""

    TEAM_LOGO = "team_logo"
    PLAYER_PORTRAIT = "player_portrait"


class ImageProcessingService:
    """Service for processing and storing images (team logos, player portraits)."""

    # Maximum dimensions by image type
    MAX_DIMENSIONS = {
        ImageType.TEAM_LOGO: (TEAM_LOGO_MAX_WIDTH, TEAM_LOGO_MAX_HEIGHT),
        ImageType.PLAYER_PORTRAIT: (PLAYER_PORTRAIT_MAX_WIDTH, PLAYER_PORTRAIT_MAX_HEIGHT),
    }

    # Subdirectories by image type
    SUBDIRECTORIES = {
        ImageType.TEAM_LOGO: TEAM_LOGOS_SUBDIR,
        ImageType.PLAYER_PORTRAIT: PLAYER_PORTRAITS_SUBDIR,
    }

    # File prefixes by image type
    FILE_PREFIXES = {
        ImageType.TEAM_LOGO: "logo",
        ImageType.PLAYER_PORTRAIT: "portrait",
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
    def get_image_directory(entity_id: int, image_type: ImageType) -> Path:
        """Get the directory path for an entity's image files."""
        subdir = ImageProcessingService.SUBDIRECTORIES[image_type]
        return Path(settings.UPLOAD_DIR) / subdir / str(entity_id)

    @staticmethod
    def get_image_path(entity_id: int, filename: str, image_type: ImageType) -> Path:
        """Get the full path for an image file."""
        entity_dir = ImageProcessingService.get_image_directory(entity_id, image_type)
        return entity_dir / filename

    @staticmethod
    def get_image_url(entity_id: int, image_type: ImageType) -> str | None:
        """Get the URL for an image."""
        entity_dir = ImageProcessingService.get_image_directory(entity_id, image_type)

        if not entity_dir.exists():
            return None

        # Look for any supported image file
        for file_path in entity_dir.iterdir():
            if file_path.suffix.lower() in ImageProcessingService.SUPPORTED_FORMATS:
                # Always use uploads endpoint since uploads are outside app directory
                try:
                    relative_path = file_path.relative_to(UPLOADS_DIR)
                    return f"{UPLOADS_URL_PREFIX}{relative_path}"
                except ValueError:
                    # Fallback for tests or edge cases
                    subdir = ImageProcessingService.SUBDIRECTORIES[image_type]
                    return f"{UPLOADS_URL_PREFIX}{subdir}/{entity_id}/{file_path.name}"

        return None

    # Legacy methods for backward compatibility
    @staticmethod
    def get_team_logo_directory(team_id: int) -> Path:
        """Get the directory path for a team's logo files."""
        return ImageProcessingService.get_image_directory(team_id, ImageType.TEAM_LOGO)

    @staticmethod
    def get_team_logo_path(team_id: int, filename: str) -> Path:
        """Get the full path for a team logo file."""
        return ImageProcessingService.get_image_path(team_id, filename, ImageType.TEAM_LOGO)

    @staticmethod
    def get_team_logo_url(team_id: int) -> str | None:
        """Get the URL for a team logo."""
        return ImageProcessingService.get_image_url(team_id, ImageType.TEAM_LOGO)

    @staticmethod
    def delete_image(entity_id: int, image_type: ImageType) -> None:
        """Delete all image files for an entity."""
        entity_dir = ImageProcessingService.get_image_directory(entity_id, image_type)
        entity_name = "team" if image_type == ImageType.TEAM_LOGO else "player"

        if entity_dir.exists():
            try:
                logger.info(
                    f"Attempting to delete {image_type.value} directory for {entity_name} {entity_id}: {entity_dir}"
                )
                shutil.rmtree(entity_dir)
                logger.info(f"Successfully deleted {image_type.value} directory for {entity_name} {entity_id}")
            except Exception as e:
                logger.error(f"Error deleting {image_type.value} directory for {entity_name} {entity_id}: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to delete {image_type.value} files") from e
        else:
            logger.info(f"{image_type.value} directory for {entity_name} {entity_id} does not exist: {entity_dir}")

    # Legacy method for backward compatibility
    @staticmethod
    def delete_team_logo(team_id: int) -> None:
        """Delete all logo files for a team."""
        ImageProcessingService.delete_image(team_id, ImageType.TEAM_LOGO)

    @staticmethod
    async def process_image(entity_id: int, file: UploadFile, image_type: ImageType) -> str:
        """
        Process and store an image.

        Args:
            entity_id: The ID of the entity (team or player)
            file: The uploaded image file
            image_type: The type of image being processed

        Returns:
            URL for the processed image: "/uploads/teams/1/logo.jpg" or "/uploads/players/1/portrait.jpg"
        """
        entity_name = "team" if image_type == ImageType.TEAM_LOGO else "player"
        file_prefix = ImageProcessingService.FILE_PREFIXES[image_type]

        try:
            # Read file contents
            contents = await file.read()

            # Validate the file
            ImageProcessingService.validate_image_file(file, contents)

            # Create entity directory
            entity_dir = ImageProcessingService.get_image_directory(entity_id, image_type)

            # Clean up existing image if it exists
            logger.info(
                f"Processing new {image_type.value} for {entity_name} {entity_id}, checking for existing images..."
            )
            ImageProcessingService.delete_image(entity_id, image_type)

            # Create directory
            logger.info(f"Creating directory for {entity_name} {entity_id}")
            entity_dir.mkdir(parents=True, exist_ok=True)

            # Determine output format and filename based on original file
            file_extension = os.path.splitext(file.filename or "")[1].lower()

            # Map file extensions to PIL format names
            format_mapping = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP"}

            output_format = format_mapping.get(file_extension, "JPEG")
            filename = f"{file_prefix}{file_extension}" if file_extension else f"{file_prefix}.jpg"

            # Open and process the image
            with Image.open(io.BytesIO(contents)) as original_image:
                # Resize to fit within max dimensions while preserving aspect ratio
                max_width, max_height = ImageProcessingService.MAX_DIMENSIONS[image_type]
                processed_image = ImageProcessingService.resize_image_to_fit(original_image, max_width, max_height)

                # Save the processed image
                output_path = ImageProcessingService.get_image_path(entity_id, filename, image_type)

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
                    image_url = f"{UPLOADS_URL_PREFIX}{relative_path}"
                except ValueError:
                    # Fallback for tests or edge cases
                    subdir = ImageProcessingService.SUBDIRECTORIES[image_type]
                    image_url = f"{UPLOADS_URL_PREFIX}{subdir}/{entity_id}/{filename}"

                logger.info(f"Successfully processed {image_type.value} for {entity_name} {entity_id}")
                return image_url

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing {image_type.value} for {entity_name} {entity_id}: {e}")
            # Clean up any partial files on error
            with contextlib.suppress(Exception):
                ImageProcessingService.delete_image(entity_id, image_type)
            raise HTTPException(status_code=500, detail=f"Failed to process {image_type.value} image") from e

    # Legacy method for backward compatibility
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
        return await ImageProcessingService.process_image(team_id, file, ImageType.TEAM_LOGO)

    # New method for player portraits
    @staticmethod
    async def process_player_portrait(player_id: int, file: UploadFile) -> str:
        """
        Process and store a player portrait.

        Args:
            player_id: The ID of the player
            file: The uploaded image file

        Returns:
            URL for the processed portrait: "/uploads/players/1/portrait.jpg"
        """
        return await ImageProcessingService.process_image(player_id, file, ImageType.PLAYER_PORTRAIT)

    @staticmethod
    def update_image_filename(entity_id: int, image_type: ImageType) -> str | None:
        """
        Update and return the image filename for an entity.
        This should be called after successful image processing to update the database.

        Returns:
            The relative path to store in the database (e.g., "teams/1/logo.png" or
            "players/1/portrait.jpg") or None if no image exists
        """
        image_url = ImageProcessingService.get_image_url(entity_id, image_type)
        if image_url and image_url.startswith(UPLOADS_URL_PREFIX):
            # Remove uploads URL prefix for database storage
            return image_url.removeprefix(UPLOADS_URL_PREFIX)

        # Fallback: look for any supported format in the entity directory
        entity_dir = ImageProcessingService.get_image_directory(entity_id, image_type)
        if entity_dir.exists():
            for file_path in entity_dir.iterdir():
                if file_path.suffix.lower() in ImageProcessingService.SUPPORTED_FORMATS:
                    subdir = ImageProcessingService.SUBDIRECTORIES[image_type]
                    return f"{subdir}/{entity_id}/{file_path.name}"

        # No image found
        return None

    # Legacy method for backward compatibility
    @staticmethod
    def update_team_logo_filename(team_id: int) -> str | None:
        """
        Update and return the logo filename for a team.
        This should be called after successful logo processing to update the database.

        Returns:
            The relative path to store in the database (e.g., "teams/1/logo.png") or None if no logo exists
        """
        return ImageProcessingService.update_image_filename(team_id, ImageType.TEAM_LOGO)

    # New methods for player portraits
    @staticmethod
    def get_player_portrait_url(player_id: int) -> str | None:
        """Get the URL for a player portrait."""
        return ImageProcessingService.get_image_url(player_id, ImageType.PLAYER_PORTRAIT)

    @staticmethod
    def delete_player_portrait(player_id: int) -> None:
        """Delete all portrait files for a player."""
        ImageProcessingService.delete_image(player_id, ImageType.PLAYER_PORTRAIT)

    @staticmethod
    def update_player_portrait_filename(player_id: int) -> str | None:
        """
        Update and return the portrait filename for a player.
        This should be called after successful portrait processing to update the database.

        Returns:
            The relative path to store in the database (e.g., "players/1/portrait.png") or None if no portrait exists
        """
        return ImageProcessingService.update_image_filename(player_id, ImageType.PLAYER_PORTRAIT)
