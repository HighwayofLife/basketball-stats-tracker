"""Custom Jinja2 templates configuration with version info."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from fastapi.templating import Jinja2Templates

from app.config import VERSION_INFO


class CustomTemplates(Jinja2Templates):
    """Custom Jinja2Templates that includes version info in all contexts."""

    def TemplateResponse(self, name: str, context: dict, **kwargs):
        """Override TemplateResponse to include version info."""
        # Add version info to context
        context["version_info"] = VERSION_INFO
        return super().TemplateResponse(name, context, **kwargs)


ImageEntityType = Literal["team", "player"]

# Entity configuration for different image types
ENTITY_CONFIG = {
    "team": {
        "model_class": "Team",
        "filename_attr": "logo_filename",
        "service_method": "get_team_logo_url",
        "subdir": "teams",
    },
    "player": {
        "model_class": "Player",
        "filename_attr": "thumbnail_image",
        "service_method": "get_player_portrait_url",
        "subdir": "players",
    },
}


@lru_cache(maxsize=256)
def _get_cached_entity_image_data(entity_id: int, entity_type: ImageEntityType) -> str | None:
    """Cached helper to get entity image filename from database.

    This function is cached to avoid repeated database queries for the same entity.
    Returns the image filename from the database, or None if not found.

    Args:
        entity_id: The ID of the entity (team or player)
        entity_type: Type of entity ("team" or "player")
    """
    from app.data_access import models
    from app.data_access.db_session import get_db_session

    try:
        config = ENTITY_CONFIG[entity_type]
        model_class = getattr(models, config["model_class"])
        filename_attr = config["filename_attr"]

        with get_db_session() as session:
            entity_obj = session.query(model_class).filter(model_class.id == entity_id).first()
            if entity_obj:
                filename = getattr(entity_obj, filename_attr, None)
                if filename:
                    return filename
            return None
    except (KeyError, AttributeError, OSError):
        return None


# Legacy cache functions for backward compatibility
@lru_cache(maxsize=128)
def _get_cached_team_logo_data(team_id: int) -> str | None:
    """Legacy cached helper for team logo data."""
    return _get_cached_entity_image_data(team_id, "team")


@lru_cache(maxsize=128)
def _get_cached_player_portrait_data(player_id: int) -> str | None:
    """Legacy cached helper for player portrait data."""
    return _get_cached_entity_image_data(player_id, "player")


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
    except (AttributeError, OSError):
        return None


def _get_entity_image_url(entity, entity_type: ImageEntityType) -> str | None:
    """Generic helper to get entity image URL."""
    if not entity:
        return None

    entity_id = getattr(entity, "id", None) or (isinstance(entity, dict) and entity.get("id"))
    if not entity_id:
        return None

    config = ENTITY_CONFIG.get(entity_type)
    if not config:
        return None

    image_filename = _get_cached_entity_image_data(entity_id, entity_type)
    if not image_filename:
        return None

    from app.config import UPLOADS_URL_PREFIX, settings

    # Ensure the path is relative to the UPLOAD_DIR
    relative_path = image_filename.removeprefix("uploads/").replace("\\", "/")
    file_path = Path(settings.UPLOAD_DIR) / relative_path

    # Use a cached file existence check
    if _check_file_exists(str(file_path)):
        return f"{UPLOADS_URL_PREFIX}{relative_path}"

    return None


def team_logo_url(team) -> str | None:
    """Jinja2 template helper to get team logo URL.

    Optimized with caching to reduce database queries and file system checks.

    Args:
        team: Team object with id attribute or dict with 'id' key
    """
    return _get_entity_image_url(team, "team")


def player_portrait_url(player) -> str | None:
    """Jinja2 template helper to get player portrait URL.

    Optimized with caching to reduce database queries and file system checks.

    Args:
        player: Player object with id attribute or dict with 'id' key
    """
    return _get_entity_image_url(player, "player")


def clear_entity_image_cache(entity_type: ImageEntityType | None = None, entity_id: int | None = None) -> None:
    """Clear cached entity image data.

    Args:
        entity_type: Type of entity to clear cache for ("team" or "player").
                   If None, clears all entity image caches.
        entity_id: If provided, would clear cache only for this entity.
                 Currently not supported by LRU cache.
    """
    if entity_type is None:
        # Clear all caches
        _get_cached_entity_image_data.cache_clear()
        _get_cached_team_logo_data.cache_clear()
        _get_cached_player_portrait_data.cache_clear()
        _check_file_exists.cache_clear()
    else:
        # Clear specific entity type cache
        # Note: LRU cache doesn't support selective clearing by specific ID
        _get_cached_entity_image_data.cache_clear()
        if entity_type == "team":
            _get_cached_team_logo_data.cache_clear()
        elif entity_type == "player":
            _get_cached_player_portrait_data.cache_clear()
        _check_file_exists.cache_clear()


def clear_team_logo_cache(team_id: int | None = None) -> None:
    """Clear cached team logo data.

    Args:
        team_id: If provided, clears cache only for this team.
                If None, clears all cached team logo data.
    """
    clear_entity_image_cache("team", team_id)


def clear_player_portrait_cache(player_id: int | None = None) -> None:
    """Clear cached player portrait data.

    Args:
        player_id: If provided, clears cache only for this player.
                 If None, clears all cached player portrait data.
    """
    clear_entity_image_cache("player", player_id)


# Setup templates
BASE_DIR = Path(__file__).resolve().parent
templates = CustomTemplates(directory=str(BASE_DIR / "templates"))

# Add custom template globals
templates.env.globals["team_logo_url"] = team_logo_url
templates.env.globals["player_portrait_url"] = player_portrait_url
