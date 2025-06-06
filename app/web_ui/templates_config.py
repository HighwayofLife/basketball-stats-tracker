"""Custom Jinja2 templates configuration with version info."""

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


def team_logo_url(team) -> str | None:
    """Jinja2 template helper to get team logo URL.

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

    # Check database first to see if team has a logo_filename
    from app.data_access import models
    from app.data_access.db_session import get_db_session

    try:
        with get_db_session() as session:
            team_obj = session.query(models.Team).filter(models.Team.id == team_id).first()
            if not team_obj or not team_obj.logo_filename:
                return None

            # Check if the file actually exists
            from pathlib import Path

            from app.config import UPLOADS_URL_PREFIX, settings

            # Handle both old and new logo_filename formats
            logo_filename = team_obj.logo_filename
            if logo_filename.startswith("uploads/"):
                # New format: uploads/teams/1/logo.png
                file_path = Path(settings.UPLOAD_DIR) / logo_filename.removeprefix("uploads/")
            elif logo_filename.startswith("teams/"):
                # Old format: teams/1/logo.png
                file_path = Path(settings.UPLOAD_DIR) / logo_filename
            else:
                # Assume it's a relative path from uploads directory
                file_path = Path(settings.UPLOAD_DIR) / logo_filename

            if file_path.exists():
                # Return the URL using the stored filename
                return f"{UPLOADS_URL_PREFIX}{logo_filename.removeprefix('uploads/')}"
            else:
                # File doesn't exist, should clean up database
                return None

    except Exception:
        # If there's any error accessing the database, fallback to filesystem check
        return ImageProcessingService.get_team_logo_url(team_id)


# Setup templates
BASE_DIR = Path(__file__).resolve().parent
templates = CustomTemplates(directory=str(BASE_DIR / "templates"))

# Add custom template globals
templates.env.globals["team_logo_url"] = team_logo_url
