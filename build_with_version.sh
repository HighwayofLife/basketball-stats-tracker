#!/bin/bash
# Build script that captures version info and builds Docker image

set -e

# Colors for output
CYAN='\033[0;36m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Get version info
APP_VERSION=$(grep -E '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/' || echo "0.2.0")
GIT_HASH=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

echo -e "${CYAN}Building with version: v${APP_VERSION}-${GIT_HASH}${NC}"

# Build Docker image with version info
docker build --target production \
    --build-arg APP_VERSION="${APP_VERSION}" \
    --build-arg GIT_HASH="${GIT_HASH}" \
    -t basketball-stats-tracker \
    .

echo -e "${GREEN}Build completed successfully!${NC}"
echo -e "${GREEN}Image tagged as: basketball-stats-tracker${NC}"
echo -e "${GREEN}Version: v${APP_VERSION}-${GIT_HASH}${NC}"