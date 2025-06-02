#!/usr/bin/env python3
"""
Version management script for basketball-stats-tracker.

This script extracts version information from pyproject.toml and provides
utilities for version management.
"""

import argparse
import re
import sys
from pathlib import Path


def get_version_from_pyproject() -> str:
    """Extract version from pyproject.toml."""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"

    if not pyproject_path.exists():
        raise FileNotFoundError(f"pyproject.toml not found at {pyproject_path}")

    content = pyproject_path.read_text(encoding="utf-8")
    version_match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)

    if not version_match:
        raise ValueError("Version not found in pyproject.toml")

    return version_match.group(1)


def increment_version(version: str, part: str) -> str:
    """Increment version number (major.minor.patch)."""
    parts = version.split(".")
    if len(parts) != 3:
        raise ValueError(f"Version must be in format major.minor.patch, got: {version}")

    major, minor, patch = map(int, parts)

    if part == "major":
        major += 1
        minor = 0
        patch = 0
    elif part == "minor":
        minor += 1
        patch = 0
    elif part == "patch":
        patch += 1
    else:
        raise ValueError(f"Part must be 'major', 'minor', or 'patch', got: {part}")

    return f"{major}.{minor}.{patch}"


def update_version_in_pyproject(new_version: str) -> None:
    """Update version in pyproject.toml."""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    content = pyproject_path.read_text(encoding="utf-8")

    # Replace version line
    new_content = re.sub(r'^version\s*=\s*["\'][^"\']+["\']', f'version = "{new_version}"', content, flags=re.MULTILINE)

    pyproject_path.write_text(new_content, encoding="utf-8")


def generate_version_json() -> None:
    """Generate VERSION.json file for local development."""
    import json
    import subprocess

    version = get_version_from_pyproject()

    try:
        git_hash = (
            subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        git_hash = "unknown"

    version_info = {"version": version, "git_hash": git_hash, "full_version": f"v{version}-{git_hash}"}

    version_json_path = Path(__file__).parent.parent / "app" / "VERSION.json"
    with open(version_json_path, "w", encoding="utf-8") as f:
        json.dump(version_info, f, indent=2)

    print(f"Generated VERSION.json: {version_info['full_version']}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Version management for basketball-stats-tracker")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Get current version
    subparsers.add_parser("get", help="Get current version from pyproject.toml")

    # Generate VERSION.json
    subparsers.add_parser("generate-json", help="Generate VERSION.json file for local development")

    # Increment version
    increment_parser = subparsers.add_parser("increment", help="Increment version")
    increment_parser.add_argument("part", choices=["major", "minor", "patch"], help="Version part to increment")
    increment_parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be changed without making changes"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        if args.command == "get":
            version = get_version_from_pyproject()
            print(version)

        elif args.command == "generate-json":
            generate_version_json()

        elif args.command == "increment":
            current_version = get_version_from_pyproject()
            new_version = increment_version(current_version, args.part)

            if args.dry_run:
                print(f"Would increment {args.part} version: {current_version} -> {new_version}")
            else:
                update_version_in_pyproject(new_version)
                print(f"Version incremented: {current_version} -> {new_version}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
