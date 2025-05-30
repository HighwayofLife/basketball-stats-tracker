#!/usr/bin/env python3
"""Capture version information at build time."""

import json
import re
import subprocess
from pathlib import Path


def get_version_from_pyproject():
    """Read version from pyproject.toml."""
    try:
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        content = pyproject_path.read_text()
        match = re.search(r'^version = "([^"]+)"', content, re.MULTILINE)
        if match:
            return match.group(1)
    except (FileNotFoundError, AttributeError):
        pass
    return "0.2.0"  # Fallback version


def get_git_hash():
    """Get the current git commit hash."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def main():
    """Main function to capture and save version info."""
    # Read version from pyproject.toml
    version = get_version_from_pyproject()

    # Get git hash
    git_hash = get_git_hash()

    # Create version info
    version_info = {"version": version, "git_hash": git_hash, "full_version": f"v{version}-{git_hash}"}

    # Save to file
    version_file = Path(__file__).parent.parent / "app" / "VERSION.json"
    version_file.write_text(json.dumps(version_info, indent=2))

    print(f"Version info captured: {version_info['full_version']}")


if __name__ == "__main__":
    main()
