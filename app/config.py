"""
Configuration module for the Basketball Stats Tracker application.
Loads environment variables and provides configuration classes for different environments.
Handles both development and bundled (PyInstaller) environments.
"""

import os
import subprocess
import sys
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings

# Determine if running as bundled app
IS_BUNDLED = getattr(sys, "frozen", False)

# Get base directory (different for PyInstaller bundle vs. development)
# We use a bit of linter silencing since sys._MEIPASS is a special PyInstaller attribute
# that only exists at runtime in the bundled application
# ruff: noqa: SIM108
# pylint: disable=protected-access
BASE_DIR = Path(sys._MEIPASS) if IS_BUNDLED else Path(__file__).parent.parent  # type: ignore

# Define shot string mapping
# This maps each character in a shot string to a dictionary indicating the shot type and outcome
SHOT_MAPPING: dict[str, dict[str, str | bool | int]] = {
    "1": {"type": "FT", "made": True, "points": 1},
    "x": {"type": "FT", "made": False, "points": 0},
    "2": {"type": "2P", "made": True, "points": 2},
    "-": {"type": "2P", "made": False, "points": 0},
    "3": {"type": "3P", "made": True, "points": 3},
    "/": {"type": "3P", "made": False, "points": 0},
}


class Settings(BaseSettings):
    """
    Base settings for the application.
    Loads settings from environment variables, with sensible defaults for development.

    Attributes:
        DATABASE_URL (str): Database connection string.
        SECRET_KEY (Optional[str]): Secret key for Flask session security.
    """

    # Handle database path differently in bundled vs development environments
    DATABASE_URL: str = os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'data' / 'league_stats.db'}")
    SECRET_KEY: str | None = None
    DEBUG: bool = False

    # Upload directory configuration
    UPLOAD_DIR: str = os.environ.get("UPLOAD_DIR", str(BASE_DIR / "app" / "web_ui" / "static" / "uploads"))

    # Email configuration (optional - for feedback feature)
    SMTP_SERVER: str | None = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    FEEDBACK_EMAIL: str | None = None

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",  # Allow extra fields to be ignored
    }

    # Add more settings variables as needed

    @model_validator(mode="after")
    def validate_settings(self):
        """
        Validate the settings after loading from environment variables.

        Raises:
            ValueError: If any required environment variable is missing.

        Returns:
            Settings: The validated settings object.
        """
        # Base class doesn't require SECRET_KEY
        return self


class DevelopmentSettings(Settings):
    """
    Settings for development environment.
    Sets DEBUG to True and provides a default SECRET_KEY for development.
    """

    DEBUG: bool = True
    SECRET_KEY: str | None = "dev_secret_key_not_for_production"


class ProductionSettings(Settings):
    """
    Settings for production environment.
    Sets DEBUG to False and requires a proper SECRET_KEY.
    """

    DEBUG: bool = False

    @model_validator(mode="after")
    def validate_production_settings(self):
        """
        Validate production settings to ensure SECRET_KEY is properly set.

        Raises:
            ValueError: If SECRET_KEY is not set in production.

        Returns:
            ProductionSettings: The validated settings object.
        """
        if not self.SECRET_KEY:
            raise ValueError("SECRET_KEY environment variable must be set in production environment.")
        return self


# Create settings instance based on ENVIRONMENT variable
env = os.getenv("ENVIRONMENT", "development").lower()

settings = ProductionSettings() if env == "production" else DevelopmentSettings()


# Version information
def get_version_from_pyproject() -> str:
    """Read version from pyproject.toml."""
    try:
        import re

        pyproject_path = BASE_DIR / "pyproject.toml"
        if pyproject_path.exists():
            content = pyproject_path.read_text()
            match = re.search(r'^version = "([^"]+)"', content, re.MULTILINE)
            if match:
                return match.group(1)
    except (FileNotFoundError, AttributeError):
        pass
    return "0.2.0"  # Fallback version


def get_version_info() -> dict[str, str]:
    """Get version information including app version and git commit hash."""
    version = get_version_from_pyproject()
    git_hash = "unknown"

    # First, try to read from VERSION.json if it exists (for production builds)
    version_file = BASE_DIR / "app" / "VERSION.json"
    if version_file.exists():
        try:
            import json

            with open(version_file) as f:
                return json.load(f)
        except Exception:
            pass

    # Otherwise, try to get git commit hash
    import contextlib

    with contextlib.suppress(subprocess.CalledProcessError, FileNotFoundError):
        git_hash = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=BASE_DIR, stderr=subprocess.DEVNULL, text=True
        ).strip()

    return {"version": version, "git_hash": git_hash, "full_version": f"v{version}-{git_hash}"}


# Get version info at startup
VERSION_INFO = get_version_info()
