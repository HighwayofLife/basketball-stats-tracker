"""Custom Jinja2 templates configuration with version info."""

from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.config import VERSION_INFO


class CustomTemplates(Jinja2Templates):
    """Custom Jinja2Templates that includes version info in all contexts."""

    def TemplateResponse(self, name: str, context: dict, **kwargs):
        """Override TemplateResponse to include version info."""
        # Add version info to context
        context["version_info"] = VERSION_INFO
        return super().TemplateResponse(name, context, **kwargs)


# Setup templates
BASE_DIR = Path(__file__).resolve().parent
templates = CustomTemplates(directory=str(BASE_DIR / "templates"))
