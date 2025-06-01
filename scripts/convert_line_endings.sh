#!/usr/bin/env bash

# Convert all text files from CRLF to LF line endings
# Usage: ./convert_line_endings.sh

set -e

echo "Converting CRLF to LF line endings in project..."
echo "=============================================="

# Get the project root (parent of scripts directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Counter for converted files
count=0

# Find all text files and convert CRLF to LF
# Exclude binary files and common directories
find . \
    -type f \
    \( -name "*.py" -o -name "*.txt" -o -name "*.md" -o -name "*.yml" -o -name "*.yaml" \
       -o -name "*.json" -o -name "*.js" -o -name "*.jsx" -o -name "*.ts" -o -name "*.tsx" \
       -o -name "*.html" -o -name "*.css" -o -name "*.scss" -o -name "*.sh" -o -name "*.bat" \
       -o -name "*.sql" -o -name "*.ini" -o -name "*.cfg" -o -name "*.conf" -o -name "*.toml" \
       -o -name "*.env" -o -name ".gitignore" -o -name ".dockerignore" -o -name "*.csv" \
       -o -name "*.xml" -o -name "*.rst" -o -name "*.in" -o -name "*.mako" -o -name "Makefile" \
       -o -name "Dockerfile" -o -name "*.mk" \) \
    -not -path "./.git/*" \
    -not -path "./__pycache__/*" \
    -not -path "./venv/*" \
    -not -path "./.venv/*" \
    -not -path "./node_modules/*" \
    -not -path "./dist/*" \
    -not -path "./build/*" \
    -not -path "./*.egg-info/*" \
    -not -path "./htmlcov/*" \
    -not -path "./.pytest_cache/*" \
    -not -path "./.mypy_cache/*" \
    -not -path "./.tox/*" \
    -print0 | while IFS= read -r -d '' file; do
    
    # Check if file contains CRLF
    if grep -q $'\r' "$file" 2>/dev/null; then
        # Convert CRLF to LF
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' 's/\r$//' "$file"
        else
            # Linux
            sed -i 's/\r$//' "$file"
        fi
        echo "Converted: $file"
        ((count++))
    fi
done

echo "=============================================="
echo "Conversion complete!"
echo "Note: Files were converted in place."