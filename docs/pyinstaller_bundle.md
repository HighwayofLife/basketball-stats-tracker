# PyInstaller Bundle Documentation

This document explains how the PyInstaller bundle for Basketball Stats Tracker is set up and how it works.

## Overview

PyInstaller is used to create a standalone executable for the Basketball Stats Tracker application. This allows users to run the application without installing Python or any dependencies.

## Bundle Structure

- `basketball_stats.spec`: The PyInstaller specification file that defines how the application is bundled
- `bundle_app.py`: Entry point script for the PyInstaller bundle
- `build_standalone.sh`: Shell script that handles the build process across different platforms
- `hooks/pyinstaller_hook.py`: Hook script that adjusts paths and configuration at runtime

## Key Components

### 1. Entry Point (`bundle_app.py`)

This script serves as the main entry point for the PyInstaller bundle. It:
- Sets up the Python path to include the application directory
- Imports and applies the PyInstaller hook for path adjustments
- Imports and runs the application CLI

### 2. PyInstaller Hook (`hooks/pyinstaller_hook.py`)

This hook script:
- Detects whether the application is running as a frozen executable or normal Python script
- Adjusts paths and settings to work in both development and bundled environments
- Ensures the database path and other resources are correctly set up

### 3. Build Script (`build_standalone.sh`)

This script:
- Detects the operating system
- Installs build dependencies if needed
- Runs PyInstaller with the correct specification file
- Sets appropriate permissions for the executable files
- Creates a ZIP archive of the distribution

### 4. Helper Scripts for End Users

- `start.sh` (macOS/Linux): Shell script to start the application
- `start.bat` (Windows): Batch script to start the application
- `README.txt`: Instructions for using the bundled application

## Runtime Behavior

When a user runs the bundled application:

1. PyInstaller's bootstrap code unpacks resources to a temporary directory
2. `bundle_app.py` is executed
3. `hooks/pyinstaller_hook.py` adjusts paths based on the runtime environment
4. The CLI (`app.cli:cli`) is invoked to handle user commands
5. Database and resource files are accessed from the appropriate locations

## Database Handling

- The database file is stored in a `data/` directory next to the executable
- Helper scripts ensure this directory exists
- The configuration is automatically adjusted to find the database in this location

## Building for Different Platforms

The build process works across:
- macOS
- Linux
- Windows

Platform-specific handling is included in `build_standalone.sh`.

## Customization

If you need to modify the bundling process:

1. Edit `basketball_stats.spec` to change what files are included
2. Edit `hooks/pyinstaller_hook.py` to adjust runtime behavior
3. Edit `build_standalone.sh` for platform-specific build changes

## Common Issues and Solutions

### Missing Dependencies

If you encounter errors about missing modules when running the executable, add them to the `hiddenimports` list in `basketball_stats.spec`.

### File Not Found Errors

If resources can't be found at runtime, check the paths in `hooks/pyinstaller_hook.py` and ensure they're correctly adjusted for the bundled environment.

### Database Location Issues

The application expects to find or create the database in a `data/` directory next to the executable. If this isn't working, check the path handling in `hooks/pyinstaller_hook.py`.

## References

- [PyInstaller Documentation](https://pyinstaller.org/en/stable/)
- [PyInstaller Hooks](https://pyinstaller.org/en/stable/hooks.html)
- [PyInstaller Runtime Information](https://pyinstaller.org/en/stable/runtime-information.html)
