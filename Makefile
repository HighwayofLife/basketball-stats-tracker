# Makefile

# Check if GNU Make is used
ifneq (,)
.error This Makefile requires GNU Make.
endif

# --- Configuration ---

# Get the directory where the Makefile is located
CURRENT_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))

# Docker Compose configuration
COMPOSE_FILE = docker-compose.yml
COMPOSE_CMD = docker compose -f $(COMPOSE_FILE)
APP_SERVICE_NAME = app # Name of your application service in docker-compose.yml

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

# --- Docker Compose Targets ---

.PHONY: run
run: ## Build and run the application containers in detached mode.
	@echo "${GREEN}Starting application containers...${NC}"
	@$(COMPOSE_CMD) up --build -d

.PHONY: stop
stop: ## Stop and remove the application containers.
	@echo "${YELLOW}Stopping application containers...${NC}"
	@$(COMPOSE_CMD) down

.PHONY: ensure-running
ensure-running: ## Check if containers are running, start them if they aren't.
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

.PHONY: logs
logs: ## Follow logs from the application container.
	@echo "${CYAN}Following logs... (Press Ctrl+C to stop)${NC}"
	@$(COMPOSE_CMD) logs -f $(APP_SERVICE_NAME)

.PHONY: shell
shell: ensure-running ## Open a shell inside the running application container.
	@echo "${CYAN}Opening shell in container '${APP_SERVICE_NAME}'...${NC}"
	@$(COMPOSE_CMD) exec $(APP_SERVICE_NAME) bash

# --- Code Quality & Testing Targets (executed inside the container) ---

.PHONY: test
test: ensure-running ## Run tests using pytest inside the container.
	@echo "${CYAN}Running tests...${NC}"
	@$(COMPOSE_CMD) exec $(APP_SERVICE_NAME) pytest

.PHONY: coverage
coverage: ensure-running ## Run tests with coverage reporting inside the container.
	@echo "${CYAN}Running tests with coverage...${NC}"
	@$(COMPOSE_CMD) exec $(APP_SERVICE_NAME) pytest # pytest config in pyproject.toml handles coverage flags

.PHONY: lint
lint: ensure-running ## Run Ruff linter inside the container.
	@echo "${CYAN}Running linter (Ruff)...${NC}"
	@$(COMPOSE_CMD) exec $(APP_SERVICE_NAME) ruff check .

.PHONY: format
format: ensure-running ## Run Ruff formatter inside the container.
	@echo "${CYAN}Running formatter (Ruff)...${NC}"
	@$(COMPOSE_CMD) exec $(APP_SERVICE_NAME) ruff format .

.PHONY: debug
debug: ## Start the application with the debugger attached (listening on port 5678).
	@echo "${PURPLE}Starting application in DEBUG mode (listening on port 5678)...${NC}"
	@$(COMPOSE_CMD) run --rm --service-ports $(APP_SERVICE_NAME) \
	  python -m debugpy --listen 0.0.0.0:5678 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# --- Local Development (without Docker) ---

.PHONY: local-init-db
local-init-db: ## Initialize database locally (without Docker).
	@echo "${CYAN}Initializing database locally...${NC}"
	@basketball-stats init-db

.PHONY: local-reset-db
local-reset-db: ## Reset database locally (without Docker). WARNING: Destroys all data.
	@echo "${RED}WARNING: This will delete all local data in the database!${NC}"
	@echo "${RED}Press Ctrl+C to cancel or Enter to continue...${NC}"
	@read
	@echo "${CYAN}Resetting database locally...${NC}"
	@basketball-stats init-db --force

.PHONY: local-init-db-migration
local-init-db-migration: ## Create a new Alembic migration locally (without Docker).
	@echo "${CYAN}Creating new database migration locally...${NC}"
	@basketball-stats init-db --migration

.PHONY: local-init-db-seed-data
local-init-db-seed-data: ## Seed the database locally with sample data for development.
	@echo "${CYAN}Seeding database with development data locally...${NC}"
	@basketball-stats seed-db

.PHONY: local-db-health
local-db-health: ## Check database health locally (without Docker).
	@echo "${CYAN}Checking database health locally...${NC}"
	@basketball-stats health-check

# --- Database Targets ---

.PHONY: init-db
init-db: ensure-running ## Initialize or upgrade the database schema using Alembic migrations (idempotent).
	@echo "${CYAN}Initializing database schema...${NC}"
	@$(COMPOSE_CMD) exec $(APP_SERVICE_NAME) basketball-stats init-db

.PHONY: reset-db
reset-db: ensure-running ## Force recreation of database (WARNING: Destroys all data).
	@echo "${RED}WARNING: This will delete all data in the database!${NC}"
	@echo "${RED}Press Ctrl+C to cancel or Enter to continue...${NC}"
	@read
	@echo "${CYAN}Resetting database...${NC}"
	@$(COMPOSE_CMD) exec $(APP_SERVICE_NAME) basketball-stats init-db --force
	
.PHONY: init-db-migration
init-db-migration: ensure-running ## Create a new Alembic migration based on model changes.
	@echo "${CYAN}Creating new database migration...${NC}"
	@$(COMPOSE_CMD) exec $(APP_SERVICE_NAME) basketball-stats init-db --migration

.PHONY: init-db-seed-data
init-db-seed-data: ensure-running ## Seed the database with sample data for development.
	@echo "${CYAN}Seeding database with development data...${NC}"
	@$(COMPOSE_CMD) exec $(APP_SERVICE_NAME) basketball-stats seed-db

.PHONY: db-health
db-health: ensure-running ## Check database connectivity.
	@echo "${CYAN}Checking database connectivity...${NC}"
	@$(COMPOSE_CMD) exec $(APP_SERVICE_NAME) basketball-stats health-check

# --- Cleaning Targets ---

.PHONY: clean
clean: ## Remove temporary files (pycache, pytest cache, coverage reports, build artifacts).
	@echo "${YELLOW}Cleaning up temporary files...${NC}"
	@find . -type f -name '*.py[co]' -delete -o -type d -name __pycache__ -delete -o -type d -name .pytest_cache -delete
	@rm -rf htmlcov/ reports/ build/ dist/ *.egg-info/ .coverage

# --- Help Target ---

########################################################################
## Self-Documenting Makefile Help                                     ##
## https://marmelab.com/blog/2016/02/29/auto-documented-makefile.html ##
########################################################################
.PHONY: help
help:
	@echo ""
	@echo "${CYAN}Usage:${NC}"
	@echo "  make [target]"
	@echo ""
	@echo "${CYAN}Available targets:${NC}"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  ${GREEN}%-15s${NC} %s\n", $$1, $$2}'
	@echo ""
