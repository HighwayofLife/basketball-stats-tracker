#!/bin/bash

# Startup script for Basketball Stats Tracker bundled application
# This script helps handle common issues with bundled PyInstaller applications

# Get directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Make data directory if it doesn't exist
mkdir -p "$DIR/data"

# Run the bundled application with any arguments passed to this script
"$DIR/basketball-stats" "$@"
