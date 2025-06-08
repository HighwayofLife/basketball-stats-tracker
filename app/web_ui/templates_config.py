"""Custom Jinja2 templates configuration with version info."""

from functools import lru_cache
from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.config import VERSION_INFO
from app.services.image_processing_service import ImageProcessingService


class CustomTemplates(Jinja2Templates):
    """Custom Jinja2Templates that includes version info in all contexts."""

    def TemplateResponse(self, name: str, context: dict, **kwargs):
        """Override TemplateResponse to include version info."""
        # Add version info to context
        context["version_info"] = VERSION_INFO
        return super().TemplateResponse(name, context, **kwargs)


@lru_cache(maxsize=128)
def _get_cached_team_logo_data(team_id: int) -> str | None:
    """Cached helper to get team logo filename from database.

    This function is cached to avoid repeated database queries for the same team.
    Returns the logo_filename from the database, or None if not found.
    """
    from app.data_access import models
    from app.data_access.db_session import get_db_session

    try:
        with get_db_session() as session:
            team_obj = session.query(models.Team).filter(models.Team.id == team_id).first()
            if team_obj and team_obj.logo_filename:
                return team_obj.logo_filename
            return None
    except Exception:
        return None


@lru_cache(maxsize=256)
def _check_file_exists(file_path_str: str) -> bool:
    """Cached helper to check if a file exists on disk."""
    return Path(file_path_str).exists()


def _get_team_logo_data_uncached(team_id: int) -> str | None:
    """Non-cached version for testing purposes."""
    from app.data_access import models
    from app.data_access.db_session import get_db_session

    try:
        with get_db_session() as session:
            team_obj = session.query(models.Team).filter(models.Team.id == team_id).first()
            if team_obj and team_obj.logo_filename:
                return team_obj.logo_filename
            return None
    except Exception:
        return None


def team_logo_url(team) -> str | None:
    """Jinja2 template helper to get team logo URL.

    Optimized with caching to reduce database queries and file system checks.

    Args:
        team: Team object with id attribute or dict with 'id' key
    """
    if not team:
        return None

    # Extract team_id from object or dict
    team_id = None
    if hasattr(team, "id"):
        team_id = team.id
    elif isinstance(team, dict) and "id" in team:
        team_id = team["id"]

    if not team_id:
        return None

    try:
        # Use cached database lookup (for performance in production)
        # For testing, the cache may interfere with mocks, but tests can clear cache
        logo_filename = _get_cached_team_logo_data(team_id)
        if not logo_filename:
            return None

        from app.config import UPLOADS_URL_PREFIX, settings

        # Handle both old and new logo_filename formats
        if logo_filename.startswith("uploads/"):
            # New format: uploads/teams/1/logo.png
            file_path = Path(settings.UPLOAD_DIR) / logo_filename.removeprefix("uploads/")
        elif logo_filename.startswith("teams/"):
            # Old format: teams/1/logo.png
            file_path = Path(settings.UPLOAD_DIR) / logo_filename
        else:
            # Assume it's a relative path from uploads directory
            file_path = Path(settings.UPLOAD_DIR) / logo_filename

        # Check if file exists (uses cached check for performance)
        if file_path.exists():
            # Return the URL using the stored filename
            return f"{UPLOADS_URL_PREFIX}{logo_filename.removeprefix('uploads/')}"
        else:
            # File doesn't exist, return None
            return None

    except Exception:
        # If there's any error, fallback to filesystem check
        try:
            return ImageProcessingService.get_team_logo_url(team_id)
        except Exception:
            return None


def clear_team_logo_cache(team_id: int | None = None) -> None:
    """Clear cached team logo data.

    Args:
        team_id: If provided, clears cache only for this team.
                If None, clears all cached team logo data.
    """
    if team_id is not None:
        # Clear specific team's cache entry
        _get_cached_team_logo_data.cache_clear()  # Note: LRU cache doesn't support selective clearing
    else:
        # Clear all cached data
        _get_cached_team_logo_data.cache_clear()
        _check_file_exists.cache_clear()


# Setup templates
BASE_DIR = Path(__file__).resolve().parent
templates = CustomTemplates(directory=str(BASE_DIR / "templates"))

# Add custom template globals
templates.env.globals["team_logo_url"] = team_logo_url
