#!/usr/bin/env python3
"""
Bundling script for Basketball Stats Tracker.
This script is used with PyInstaller to create a standalone executable.
"""

import os
import sys

# Ensure the app directory is in the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# ruff: noqa: E402, I001
# pylint: disable=wrong-import-position, ungrouped-imports
from hooks.pyinstaller_hook import adjust_config_paths
adjust_config_paths()

from app.cli import cli  # noqa: E402

if __name__ == "__main__":
    cli()
