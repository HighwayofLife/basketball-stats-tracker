"""
PyInstaller hook to handle runtime adjustments for Basketball Stats Tracker.
This file is used to fix paths and ensure resources are accessible in the bundled app.
"""

import os
import sys
from pathlib import Path


def get_app_path():
    """Get the application base path whether running as script or frozen executable."""
    if getattr(sys, "frozen", False):
        # If the application is frozen (PyInstaller)
        # pylint: disable=protected-access
        return Path(sys._MEIPASS)  # type: ignore
    else:
        # If running as a normal Python script
        return Path(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))


def adjust_config_paths():
    """
    Adjust configuration paths to work in both development and bundled environments.
    Call this early in application startup.
    """
    app_path = get_app_path()

    # Set environment variable for database path
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{app_path}/data/league_stats.db")

    # Ensure data directory exists
    data_dir = app_path / "data"
    data_dir.mkdir(exist_ok=True)

    # Set Alembic environment variable if needed
    os.environ.setdefault("ALEMBIC_CONFIG", str(app_path / "alembic.ini"))

    return app_path


# Adjust paths when imported
app_path = adjust_config_paths()
