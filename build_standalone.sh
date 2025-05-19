#!/bin/bash
# Build script for creating standalone executables for Basketball Stats Tracker
# This script detects the OS and runs the appropriate PyInstaller commands

set -e  # Exit on any error

echo "🏀 Building Basketball Stats Tracker standalone application"

# Install build dependencies if needed
if ! command -v pyinstaller >/dev/null 2>&1; then
    echo "Installing build dependencies..."
    pip install -e ".[build]"
fi

# Detect operating system
OS="$(uname -s)"
case "${OS}" in
    Linux*)     OS_NAME=Linux;;
    Darwin*)    OS_NAME=macOS;;
    CYGWIN*|MINGW*|MSYS*) OS_NAME=Windows;;
    *)          OS_NAME="UNKNOWN:${OS}"
esac

echo "Detected operating system: ${OS_NAME}"

# Clean previous build artifacts
rm -rf build/basketball-stats build/basketball-stats-cli
rm -rf dist/basketball-stats dist/basketball-stats-cli

# Build with PyInstaller
echo "Building with PyInstaller..."
pyinstaller basketball_stats.spec

# Post-process the build based on OS
if [ "${OS_NAME}" = "macOS" ] || [ "${OS_NAME}" = "Linux" ]; then
    echo "Setting file permissions..."
    chmod +x dist/basketball-stats/basketball-stats
    chmod +x dist/basketball-stats/start.sh
elif [ "${OS_NAME}" = "Windows" ]; then
    echo "Packaging for Windows..."
    # No special steps needed for Windows
else
    echo "Unknown OS, skipping OS-specific steps"
fi

# Create a ZIP archive of the distribution
echo "Creating distribution package..."
cd dist
ZIP_NAME="basketball-stats-${OS_NAME}.zip"
if [ "${OS_NAME}" = "Windows" ]; then
    # Use PowerShell to create ZIP on Windows
    powershell -Command "Compress-Archive -Path basketball-stats -DestinationPath ${ZIP_NAME}"
else
    # Use zip on macOS/Linux
    zip -r "${ZIP_NAME}" basketball-stats
fi

echo "✅ Build complete!"
echo "Standalone executable is in: dist/basketball-stats/"
echo "ZIP package created: dist/${ZIP_NAME}"
