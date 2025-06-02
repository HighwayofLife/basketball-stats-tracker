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

# Version information
APP_VERSION = 0.4.5
GIT_HASH = $(shell git rev-parse --short HEAD 2>/dev/null || echo "unknown")

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
	@echo "${CYAN}Building production Docker image with version v$(APP_VERSION)-$(GIT_HASH)...${NC}"
	@docker build --target production \
		--build-arg APP_VERSION=$(APP_VERSION) \
		--build-arg GIT_HASH=$(GIT_HASH) \
		-t $(IMAGE_NAME) .

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
test: ## Run all tests (unit, integration, and UI validation)
	@echo "${CYAN}Running comprehensive test suite...${NC}"
	@echo "${YELLOW}Step 1: Running unit and integration tests in container${NC}"
	@$(MAKE) test-container
	@echo "${YELLOW}Step 2: Running UI validation tests${NC}"
	@$(MAKE) test-ui-standalone

.PHONY: test-container
test-container: ensure-running ## Run unit and integration tests inside the container
	@echo "${CYAN}Running unit and integration tests in container...${NC}"
	@$(COMPOSE_CMD) exec $(APP_SERVICE_NAME) pytest tests/unit/ tests/integration/ --ignore=tests/integration/test_ui_validation.py

.PHONY: coverage
coverage: ensure-running ## Run tests with coverage reporting inside the container
	@echo "${CYAN}Running tests with coverage...${NC}"
	@$(COMPOSE_CMD) exec $(APP_SERVICE_NAME) pytest # pytest config in pyproject.toml handles coverage flags

.PHONY: lint
lint: ensure-running ## Run Ruff linter inside the container
	@echo "${CYAN}Running linter (Ruff)...${NC}"
	@$(COMPOSE_CMD) exec $(APP_SERVICE_NAME) ruff check .

.PHONY: lint-github
lint-github: ensure-running ## Run Ruff linter with GitHub output format
	@echo "${CYAN}Running linter (Ruff) with GitHub format...${NC}"
	@$(COMPOSE_CMD) exec $(APP_SERVICE_NAME) ruff check . --output-format=github

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

.PHONY: local-test-ui
local-test-ui: ## Run UI validation tests locally (manages containers automatically)
	@echo "${CYAN}Running UI validation tests locally...${NC}"
	@pytest -v tests/integration/test_ui_validation.py

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
	@$(COMPOSE_CMD) exec $(APP_SERVICE_NAME) pytest -v tests/integration/ --ignore=tests/integration/test_ui_validation.py

.PHONY: test-ui
test-ui: ## Run UI validation tests (starts/stops containers automatically)
	@echo "${CYAN}Running UI validation tests...${NC}"
	@echo "${YELLOW}Note: This will stop any running containers first${NC}"
	@pytest -v tests/integration/test_ui_validation.py

.PHONY: test-ui-standalone
test-ui-standalone: ## Internal target for running UI tests as part of comprehensive suite
	@echo "${CYAN}Running UI validation tests (standalone)...${NC}"
	@$(COMPOSE_CMD) down >/dev/null 2>&1 || true
	@pytest -v tests/integration/test_ui_validation.py

.PHONY: test-coverage
test-coverage: ensure-running ## Run all tests with coverage reporting inside the container
	@echo "${CYAN}Running tests with coverage in container...${NC}"
	@$(COMPOSE_CMD) exec $(APP_SERVICE_NAME) pytest --cov=app --cov-report=term --cov-report=html tests/

# --- MCP Server ---

.PHONY: mcp-server
mcp-server: ## Run the Model Context Protocol server for easier database access
	@echo "${CYAN}Starting MCP server...${NC}"
	@python -m app.cli mcp-server

# --- Production Deployment ---

.PHONY: migrate-production
migrate-production: ## Run database migration on production Cloud SQL
	@echo "${CYAN}Running production database migration...${NC}"
	@echo "${YELLOW}Executing migration job on Cloud Run...${NC}"
	@gcloud run jobs execute basketball-stats-migrate --region=us-west1
	@echo "${GREEN}Migration completed! Check logs with: make migration-logs${NC}"

.PHONY: migration-logs
migration-logs: ## View recent migration logs from production
	@echo "${CYAN}Fetching migration logs...${NC}"
	@gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=basketball-stats-migrate" --limit=20 --format="table(timestamp,severity,textPayload)" --freshness=10m

.PHONY: migration-status
migration-status: ## Check status of recent migration executions
	@echo "${CYAN}Checking migration execution status...${NC}"
	@gcloud run jobs executions list --region=us-west1 --job=basketball-stats-migrate --limit=5

.PHONY: deploy-production
deploy-production: ## Deploy to production (build, push, deploy, migrate)
	@echo "${CYAN}Starting full production deployment...${NC}"
	@echo "${YELLOW}This will trigger the GitHub Actions pipeline for deployment.${NC}"
	@echo "${YELLOW}Ensure your changes are committed and pushed to main branch.${NC}"
	@echo "${RED}Press Ctrl+C to cancel or Enter to continue...${NC}"
	@read
	@echo "${CYAN}Triggering deployment via GitHub Actions...${NC}"
	@gh workflow run deploy.yml
	@echo "${GREEN}Deployment triggered! Monitor progress at: https://github.com/highwayoflife/basketball-stats-tracker/actions${NC}"

.PHONY: production-status
production-status: ## Check production service status
	@echo "${CYAN}Checking production service status...${NC}"
	@echo "${YELLOW}Cloud Run Service:${NC}"
	@gcloud run services describe basketball-stats --region=us-west1 --format="table(status.conditions[0].type,status.observedGeneration,status.url)"
	@echo ""
	@echo "${YELLOW}Cloud SQL Instance:${NC}"
	@gcloud sql instances describe basketball-stats-db --format="table(name,databaseVersion,state,ipAddresses[0].ipAddress)"
	@echo ""
	@echo "${YELLOW}Recent Application Logs:${NC}"
	@gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=basketball-stats" --limit=5 --format="table(timestamp,severity,textPayload)"

.PHONY: production-logs
production-logs: ## View production application logs
	@echo "${CYAN}Streaming production logs... (Press Ctrl+C to stop)${NC}"
	@gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=basketball-stats"

# --- Statistics ---

.PHONY: update-stats
update-stats: ## Update project statistics in README.md
	@echo "${CYAN}Updating project statistics in README.md...${NC}"
	@python scripts/update_stats.py

# --- Cleaning Targets ---

.PHONY: clean
clean: ## Remove temporary files (pycache, pytest cache, coverage reports, build artifacts)
	@echo "${YELLOW}Cleaning up temporary files...${NC}"
	@find . -type f -name '*.py[co]' -delete -o -type d -name __pycache__ -delete -o -type d -name .pytest_cache -delete
	@rm -rf htmlcov/ reports/ build/ dist/ *.egg-info/ .coverage

.PHONY: fix-line-endings
fix-line-endings: ## Convert all text files from CRLF to LF line endings
	@echo "${CYAN}Converting CRLF to LF line endings...${NC}"
	@chmod +x scripts/convert_line_endings.sh
	@./scripts/convert_line_endings.sh

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
