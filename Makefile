# Makefile

# Check if GNU Make is used
ifneq (,)
.error This Makefile requires GNU Make.
endif

# --- Configuration ---

# Get the directory where the Makefile is located
CURRENT_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))

# Docker and Docker Compose configuration
COMPOSE_FILE = docker-compose.yml
COMPOSE_CMD = docker compose -f $(COMPOSE_FILE)
APP_SERVICE_NAME = web # The web service in docker-compose.yml
IMAGE_NAME = basketball-stats-tracker
DOCKER_REGISTRY =

# Colors for terminal output
BLUE=\033[0;34m
GREEN=\033[0;32m
RED=\033[0;31m
YELLOW=\033[0;33m
PURPLE=\033[0;35m
CYAN=\033[0;36m
NC=\033[0m # No Color

# Default target when running `make`
.DEFAULT_GOAL := help

# --- Docker Targets ---

.PHONY: docker-build
docker-build: ## Build the Docker image for production
	@echo "${CYAN}Building production Docker image...${NC}"
	@docker build --target production -t $(IMAGE_NAME) .

.PHONY: docker-run
docker-run: docker-build ## Run the production Docker container
	@echo "${CYAN}Running production container...${NC}"
	@docker run -p 8000:8000 $(IMAGE_NAME)

.PHONY: docker-compose-build
docker-compose-build: ## Build the Docker images using docker-compose
	@echo "${CYAN}Building Docker images with docker-compose...${NC}"
	@$(COMPOSE_CMD) build

.PHONY: docker-clean
docker-clean: ## Clean up Docker images and containers
	@echo "${CYAN}Cleaning up Docker resources...${NC}"
	@docker ps -a -q --filter "name=$(IMAGE_NAME)" | xargs -r docker rm -f
	@docker images -q $(IMAGE_NAME) | xargs -r docker rmi -f

.PHONY: run
run: ## Build and run the application with docker-compose in detached mode
	@echo "${GREEN}Starting application containers...${NC}"
	@$(COMPOSE_CMD) up --build -d

.PHONY: stop
stop: ## Stop and remove the application containers
	@echo "${YELLOW}Stopping application containers...${NC}"
	@$(COMPOSE_CMD) down

.PHONY: ensure-running
ensure-running: ## Check if containers are running, start them if they aren't
	@echo "${BLUE}Checking if containers are running...${NC}"
	@if [ -z "$$($(COMPOSE_CMD) ps -q $(APP_SERVICE_NAME) 2>/dev/null)" ]; then \
		echo "${YELLOW}Containers not running. Starting them now...${NC}"; \
		$(MAKE) run; \
		echo "${GREEN}Waiting for containers to be ready...${NC}"; \
		sleep 3; \
	else \
		echo "${GREEN}Containers are already running.${NC}"; \
	fi

.PHONY: build
build: ## Build the Docker images for the application.
	@echo "${CYAN}Building Docker images...${NC}"
	@$(COMPOSE_CMD) build

.PHONY: shell
shell: ensure-running ## Open a shell inside the running application container
	@echo "${CYAN}Opening shell in container '${APP_SERVICE_NAME}'...${NC}"
	@$(COMPOSE_CMD) exec $(APP_SERVICE_NAME) bash

.PHONY: logs
logs: ## Follow logs from the application container
	@echo "${CYAN}Following logs... (Press Ctrl+C to stop)${NC}"
	@$(COMPOSE_CMD) logs -f $(APP_SERVICE_NAME)

# --- Code Quality & Testing Targets (executed inside the container) ---

.PHONY: test
test: ensure-running ## Run tests using pytest inside the container
	@echo "${CYAN}Running tests...${NC}"
	@$(COMPOSE_CMD) exec $(APP_SERVICE_NAME) pytest

.PHONY: coverage
coverage: ensure-running ## Run tests with coverage reporting inside the container
	@echo "${CYAN}Running tests with coverage...${NC}"
	@$(COMPOSE_CMD) exec $(APP_SERVICE_NAME) pytest # pytest config in pyproject.toml handles coverage flags

.PHONY: lint
lint: ensure-running ## Run Ruff linter inside the container
	@echo "${CYAN}Running linter (Ruff)...${NC}"
	@$(COMPOSE_CMD) exec $(APP_SERVICE_NAME) ruff check .

.PHONY: format
format: ensure-running ## Run Ruff formatter inside the container
	@echo "${CYAN}Running formatter (Ruff)...${NC}"
	@$(COMPOSE_CMD) exec $(APP_SERVICE_NAME) ruff format .

.PHONY: debug
debug: ## Start the application with the debugger attached (listening on port 5678)
	@echo "${PURPLE}Starting application in DEBUG mode (listening on port 5678)...${NC}"
	@$(COMPOSE_CMD) run --rm --service-ports $(APP_SERVICE_NAME) python -m debugpy --listen 0.0.0.0:5678 --wait-for-client -m app.cli web-server --host 0.0.0.0 --port 8000

.PHONY: debug-web
debug-web: ## Start the web UI server with the debugger attached (using uvicorn directly)
	@echo "${PURPLE}Starting web UI in DEBUG mode with uvicorn (listening on port 5678)...${NC}"
	@$(COMPOSE_CMD) run --rm --service-ports $(APP_SERVICE_NAME) python -m debugpy --listen 0.0.0.0:5678 --wait-for-client -m uvicorn app.web_ui:app --host 0.0.0.0 --port 8000 --reload

# --- Local Development (without Docker) ---

.PHONY: local-init-db
local-init-db: ## Initialize database locally (without Docker).
	@echo "${CYAN}Initializing database locally...${NC}"
	@python -m app.cli init-db

.PHONY: local-reset-db
local-reset-db: ## Reset database locally (without Docker). WARNING: Destroys all data.
	@echo "${RED}WARNING: This will delete all local data in the database!${NC}"
	@echo "${RED}Press Ctrl+C to cancel or Enter to continue...${NC}"
	@read
	@echo "${CYAN}Resetting database locally...${NC}"
	@python -m app.cli init-db --force

.PHONY: local-init-db-migration
local-init-db-migration: ## Create a new Alembic migration locally (without Docker).
	@echo "${CYAN}Creating new database migration locally...${NC}"
	@python -m app.cli init-db --migration

.PHONY: local-first-time-setup
local-first-time-setup: ## First-time setup: Create migrations and initialize database (required for new projects).
	@echo "${CYAN}Performing first-time database setup...${NC}"
	@python -m app.cli init-db --migration
	@echo "${GREEN}Database initialized with migrations. Now you can import data.${NC}"

.PHONY: local-init-db-seed-data
local-init-db-seed-data: ## Seed the database locally with sample data for development.
	@echo "${CYAN}Seeding database with development data locally...${NC}"
	@basketball-stats seed-db

.PHONY: local-db-health
local-db-health: ## Check database health locally (without Docker).
	@echo "${CYAN}Checking database health locally...${NC}"
	@basketball-stats health-check

.PHONY: local-import-roster
local-import-roster: ## Import roster from a CSV file locally (without Docker).
	@echo "${CYAN}Importing roster locally...${NC}"
	@# Example: make local-import-roster ROSTER_FILE=players_template.csv
	@basketball-stats import-roster --file $(ROSTER_FILE)

.PHONY: local-import-game-stats
local-import-game-stats: ## Import game statistics from a CSV file locally (without Docker).
	@echo "${CYAN}Importing game statistics locally...${NC}"
	@# Example: make local-import-game-stats GAME_STATS_FILE=game_stats_template.csv
	@basketball-stats import-game --file $(GAME_STATS_FILE)

# --- Database Targets ---

.PHONY: init-db
init-db: ensure-running ## Initialize or upgrade the database schema using Alembic migrations (idempotent)
	@echo "${CYAN}Initializing database schema...${NC}"
	@$(COMPOSE_CMD) exec $(APP_SERVICE_NAME) basketball-stats init-db

.PHONY: reset-db
reset-db: ensure-running ## Force recreation of database (WARNING: Destroys all data)
	@echo "${RED}WARNING: This will delete all data in the database!${NC}"
	@echo "${RED}Press Ctrl+C to cancel or Enter to continue...${NC}"
	@read
	@echo "${CYAN}Resetting database...${NC}"
	@$(COMPOSE_CMD) exec $(APP_SERVICE_NAME) basketball-stats init-db --force

.PHONY: init-db-migration
init-db-migration: ensure-running ## Create a new Alembic migration based on model changes
	@echo "${CYAN}Creating new database migration...${NC}"
	@$(COMPOSE_CMD) exec $(APP_SERVICE_NAME) basketball-stats init-db --migration

.PHONY: seed-db
seed-db: ensure-running ## Seed the database with sample data for development
	@echo "${CYAN}Seeding database with development data...${NC}"
	@$(COMPOSE_CMD) exec $(APP_SERVICE_NAME) basketball-stats seed-db

.PHONY: db-health
db-health: ensure-running ## Check database connectivity
	@echo "${CYAN}Checking database connectivity...${NC}"
	@$(COMPOSE_CMD) exec $(APP_SERVICE_NAME) basketball-stats health-check

.PHONY: import-roster
import-roster: ensure-running ## Import roster from a CSV file into the container's database
	@echo "${CYAN}Importing roster into container...${NC}"
	@# Example: make import-roster ROSTER_FILE=players_template.csv
	@# Note: The ROSTER_FILE path must be accessible from where docker compose is run,
	@# or you might need to adjust volume mounts if the file is inside the container.
	@# This example assumes the CSV is in the project root and accessible to the 'web' service.
	@$(COMPOSE_CMD) exec $(APP_SERVICE_NAME) basketball-stats import-roster --file $(ROSTER_FILE)

.PHONY: import-game-stats
import-game-stats: ensure-running ## Import game statistics from a CSV file into the container's database
	@echo "${CYAN}Importing game statistics into container...${NC}"
	@# Example: make import-game-stats GAME_STATS_FILE=game_stats_example.csv
	@# Note: The GAME_STATS_FILE path must be accessible from where docker compose is run,
	@# or you might need to adjust volume mounts if the file is inside the container.
	@# This example assumes the CSV is in the project root and accessible to the 'web' service.
	@$(COMPOSE_CMD) exec $(APP_SERVICE_NAME) basketball-stats import-game --file $(GAME_STATS_FILE)

# --- Testing Targets (Local) ---

.PHONY: local-test
local-test: ## Run all tests locally with pytest
	@echo "${CYAN}Running all tests locally...${NC}"
	@pytest -v

.PHONY: local-test-unit
local-test-unit: ## Run unit tests only locally
	@echo "${CYAN}Running unit tests locally...${NC}"
	@pytest -v tests/unit/

.PHONY: local-test-integration
local-test-integration: ## Run integration tests only locally
	@echo "${CYAN}Running integration tests locally...${NC}"
	@pytest -v tests/integration/

.PHONY: local-test-coverage
local-test-coverage: ## Run tests with coverage report locally
	@echo "${CYAN}Running tests with coverage locally...${NC}"
	@pytest --cov=app --cov-report=term --cov-report=html tests/

.PHONY: local-test-watch
local-test-watch: ## Run tests in watch mode locally, rerunning on file changes
	@echo "${CYAN}Running tests in watch mode locally...${NC}"
	@pytest-watch -- -v tests/

# --- Convenience Testing Targets (delegates to container) ---

.PHONY: test-unit
test-unit: ensure-running ## Run unit tests inside the container
	@echo "${CYAN}Running unit tests in container...${NC}"
	@$(COMPOSE_CMD) exec $(APP_SERVICE_NAME) pytest -v tests/unit/

.PHONY: test-integration
test-integration: ensure-running ## Run integration tests inside the container
	@echo "${CYAN}Running integration tests in container...${NC}"
	@$(COMPOSE_CMD) exec $(APP_SERVICE_NAME) pytest -v tests/integration/

# --- MCP Server ---

.PHONY: mcp-server
mcp-server: ## Run the Model Context Protocol server for easier database access
	@echo "${CYAN}Starting MCP server...${NC}"
	@python -m app.cli mcp-server

# --- Cleaning Targets ---

.PHONY: clean
clean: ## Remove temporary files (pycache, pytest cache, coverage reports, build artifacts)
	@echo "${YELLOW}Cleaning up temporary files...${NC}"
	@find . -type f -name '*.py[co]' -delete -o -type d -name __pycache__ -delete -o -type d -name .pytest_cache -delete
	@rm -rf htmlcov/ reports/ build/ dist/ *.egg-info/ .coverage

# --- Package Application ---

.PHONY: install-build-deps
install-build-deps: ## Install build dependencies for packaging the application
	@echo "${CYAN}Installing build dependencies...${NC}"
	@pip install -e ".[build]"

.PHONY: bundle
bundle: install-build-deps ## Bundle the application into a standalone executable using PyInstaller
	@echo "${CYAN}Building standalone executable with PyInstaller...${NC}"
	@chmod +x build_standalone.sh
	@./build_standalone.sh
	@echo "${GREEN}Build complete! Executable is in ./dist/basketball-stats${NC}"

.PHONY: clean-bundle
clean-bundle: ## Clean up PyInstaller build artifacts
	@echo "${YELLOW}Cleaning up PyInstaller build artifacts...${NC}"
	@rm -rf build/basketball-stats build/basketball-stats-cli
	@rm -rf dist/basketball-stats dist/basketball-stats-cli
	@echo "${GREEN}PyInstaller build artifacts removed.${NC}"

# --- Help Target ---

########################################################################
## Self-Documenting Makefile Help                                     ##
## https://marmelab.com/blog/2016/02/29/auto-documented-makefile.html ##
########################################################################
.PHONY: help
help:
	@echo ""
	@echo "${CYAN}Basketball Stats Tracker - Build & Development Tools${NC}"
	@echo ""
	@echo "${CYAN}Usage:${NC}"
	@echo "  make [target]"
	@echo ""
	@echo "${CYAN}Available Targets:${NC}"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  ${GREEN}%-20s${NC} %s\n", $$1, $$2}'
	@echo ""
