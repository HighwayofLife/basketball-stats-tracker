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


def team_logo_url(team, size: str = "120x120") -> str | None:
    """Jinja2 template helper to get team logo URL."""
    if not team or not hasattr(team, "id"):
        return None
    return ImageProcessingService.get_team_logo_url(team.id, size)


# Setup templates
BASE_DIR = Path(__file__).resolve().parent
templates = CustomTemplates(directory=str(BASE_DIR / "templates"))

# Add custom template globals
templates.env.globals["team_logo_url"] = team_logo_url
