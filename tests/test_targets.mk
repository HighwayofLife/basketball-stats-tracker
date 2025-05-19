# --- Testing Targets ---

.PHONY: test
test: ## Run all tests with pytest
	@echo "${CYAN}Running all tests...${NC}"
	@pytest -v

.PHONY: test-unit
test-unit: ## Run unit tests only
	@echo "${CYAN}Running unit tests...${NC}"
	@pytest -v tests/unit/

.PHONY: test-integration
test-integration: ## Run integration tests only
	@echo "${CYAN}Running integration tests...${NC}"
	@pytest -v tests/integration/

.PHONY: test-coverage
test-coverage: ## Run tests with coverage report
	@echo "${CYAN}Running tests with coverage...${NC}"
	@pytest --cov=app --cov-report=term --cov-report=html tests/

.PHONY: test-watch
test-watch: ## Run tests in watch mode, rerunning on file changes
	@echo "${CYAN}Running tests in watch mode...${NC}"
	@pytest-watch -- -v tests/
