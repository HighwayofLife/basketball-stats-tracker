#!/usr/bin/env python3
"""
Convert all text files in the project from CRLF to LF line endings.
"""

import os
import sys
from pathlib import Path

# File extensions to process
TEXT_EXTENSIONS = {
    ".py",
    ".txt",
    ".md",
    ".yml",
    ".yaml",
    ".json",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".html",
    ".css",
    ".scss",
    ".sh",
    ".bat",
    ".sql",
    ".ini",
    ".cfg",
    ".conf",
    ".toml",
    ".env",
    ".gitignore",
    ".dockerignore",
    ".csv",
    ".xml",
    ".rst",
    ".in",
    ".mako",
}

# Directories to skip
SKIP_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "env",
    ".tox",
    ".pytest_cache",
    "htmlcov",
    ".mypy_cache",
    "dist",
    "build",
    ".egg-info",
    "basketball_stats_tracker.egg-info",
}


def is_text_file(file_path):
    """Check if file should be processed based on extension."""
    return file_path.suffix.lower() in TEXT_EXTENSIONS


def is_binary(file_path):
    """Check if file is binary by reading first few bytes."""
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(512)
            if b"\0" in chunk:
                return True
            # Check for common binary signatures
            if chunk.startswith((b"PK", b"GIF", b"PNG", b"\x89PNG", b"\xff\xd8\xff")):
                return True
        return False
    except OSError:
        return True


def convert_file(file_path):
    """Convert CRLF to LF in a single file."""
    try:
        # Skip binary files
        if is_binary(file_path):
            return False

        # Read file content
        with open(file_path, "rb") as f:
            content = f.read()

        # Check if file has CRLF
        if b"\r\n" not in content:
            return False

        # Convert CRLF to LF
        new_content = content.replace(b"\r\n", b"\n")

        # Write back
        with open(file_path, "wb") as f:
            f.write(new_content)

        return True
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """Main function to convert line endings in entire project."""
    # Get project root (parent of scripts directory)
    project_root = Path(__file__).parent.parent

    converted_count = 0
    error_count = 0

    print(f"Converting CRLF to LF in project: {project_root}")
    print("=" * 60)

    # Walk through all files
    for root, dirs, files in os.walk(project_root):
        # Skip directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        root_path = Path(root)

        for file in files:
            file_path = root_path / file

            # Skip non-text files based on extension
            if not is_text_file(file_path):
                continue

            # Convert file
            if convert_file(file_path):
                relative_path = file_path.relative_to(project_root)
                print(f"Converted: {relative_path}")
                converted_count += 1

    print("=" * 60)
    print("Conversion complete!")
    print(f"Files converted: {converted_count}")

    if error_count > 0:
        print(f"Errors encountered: {error_count}")
        sys.exit(1)


if __name__ == "__main__":
    main()
