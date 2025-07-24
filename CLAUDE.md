# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Commands

### Development & Testing
```bash
# First-time setup
make local-first-time-setup    # DB migration + sample data import

# Python environment
source venv/bin/activate       # Activate virtual environment before Python commands
pip install ".[dev]"          # Install dependencies using pyproject.toml

# Run the application (Docker)
make run

# Run tests
make test              # All tests
make test-unit        # Unit tests only
make test-integration # Integration tests only
make test-ui          # UI validation tests (starts/stops containers)
make test-coverage    # With coverage report
make test-cleanup     # Clean up test database and reset all test data
pytest                # Direct pytest execution (after activating venv)

# Code quality
make lint    # Run ruff linter
make format  # Format code with ruff
ruff format --target-version py311 <dir|file>  # Format specific files

# Database operations
make init-db   # Initialize database
make reset-db  # Reset database
make seed-db   # Seed with demo data

# Version management
make version                    # Show current version
make version-increment-patch    # Increment patch version (1.2.3 -> 1.2.4)
make version-increment-minor    # Increment minor version (1.2.3 -> 1.3.0)
make version-increment-major    # Increment major version (1.2.3 -> 2.0.0)
make version-generate-json      # Generate VERSION.json for local development

# Build standalone executable
make bundle    # Creates dist/basketball-stats executable
```

### CLI Commands
```bash
# Import player roster
basketball-stats import-roster <csv_file>

# Import game statistics
basketball-stats import-game <csv_file>

# Generate reports
basketball-stats report game <game_id> [--format console|csv]
basketball-stats report player-season <player_id> [--format console|csv]

# Player of the Week awards
basketball-stats calculate-potw                    # Calculate for all seasons
basketball-stats calculate-potw --season 2024     # Calculate for specific season
basketball-stats calculate-potw --recalculate     # Reset and recalculate all awards

# Database management
basketball-stats init-db
basketball-stats seed-db

# MCP Server
python -m app.cli mcp-server  # HTTP API server
```

### Production Deployment Commands
```bash
# Production database migration
make migrate-production      # Run database migration on production Cloud SQL
make migration-logs         # View recent migration logs
make migration-status       # Check migration execution status

# Production deployment and monitoring
make deploy-production      # Trigger full deployment via GitHub Actions
make production-status      # Check Cloud Run and Cloud SQL status
make production-logs        # Stream live production logs
```

## Architecture Overview

### Layered Architecture
The application uses a clean layered architecture with clear separation of concerns:

1. **CLI Layer** (`app/cli.py`): Command-line interface using Click/Typer framework
2. **Service Layer** (`app/services/`): Business logic and orchestration
   - `csv_import_service.py`: Handles CSV parsing and data import
   - `game_service.py`: Game-related operations
   - `player_service.py`: Player management
   - `stats_entry_service.py`: Statistics data entry
3. **Data Access Layer** (`app/data_access/`): Database operations
   - `models.py`: SQLAlchemy models (Team, Player, Game, PlayerGameStats, PlayerQuarterStats)
   - `crud/`: CRUD operations for each model
   - `database_manager.py`: Database initialization and management
4. **Utilities** (`app/utils/`):
   - `input_parser.py`: Parses shot strings (e.g., "22-1x" = 2 made 2pts, 1 missed 2pt, 1 made FT, 1 missed FT)
   - `stats_calculator.py`: Calculates derived statistics

### Key Design Patterns
- **Repository Pattern**: CRUD operations isolated in `data_access/crud/`
- **Service Layer Pattern**: Business logic in services, not in models or controllers
- **Dependency Injection**: Database sessions passed through layers
- **Schema Validation**: Pydantic models for CSV import validation

## Database Schema

The application uses SQLAlchemy with SQLite (development) or PostgreSQL (production):

- **Team**: id, name
- **Player**: id, name, team_id, jersey_number, position, height, weight, year
- **Game**: id, game_date, home_team_id, away_team_id, home_score, away_score
- **PlayerGameStats**: Aggregated stats per player per game
- **PlayerQuarterStats**: Quarter-by-quarter breakdown

Migrations are managed with Alembic (`alembic upgrade head`).

## Testing Strategy

Tests are organized by type and mirror the source structure:
- **Unit tests** (`tests/unit/`): Test individual functions and classes in isolation
- **Integration tests** (`tests/integration/`): Test full workflows like CSV import
- **Fixtures** in `conftest.py`: Provide test database sessions and CLI runners
- **Target**: ≥ 90% test coverage
- **Framework**: pytest with fixtures for clean testing
- **Requirements**: Python 3.11+, strict type hints (mypy --strict must pass)
- Whenever adding, changing, or removing any implementation, always run tests to be sure we didn't break anything. If new features or functionality are added, create new tests to test that feature/function.

## Workflow Memories
- **For significant changes**: Consider running `make version-increment-patch` to update version and document in CHANGELOG.md
- After implementing code, create/update the unit and integration tests, then run the test suites
- If you get "no module named" errors, update the pyproject.toml and be sure we source the python env, then run `pip install ".[dev]"`
- **Authentication issues should be caught by tests** - Always create proper test coverage for authentication requirements
- **Don't rebuild containers for code changes** - Only rebuild when dependencies change; code is auto-reloaded via volume mounts
- **Test changes directly** - After making code changes, immediately test both success and failure scenarios rather than just checking logs
- **Use existing admin credentials** - username: `admin`, password from `.env` file `ADMIN_PASSWORD` instead of creating new users
- **Stay on current branch** - Don't switch branches unnecessarily unless explicitly requested

## Memory: Developer Workflow & Documentation Guidelines
- If unsure what commands to run, consult the developer documentation
- Routinely update the developer documentation with useful/common commands that are needed
- Run tests after completing changes/task lists to be sure it didn't break anything
- Add/update tests as needed after completing changes
- But keep things simple

## Memory: CHANGELOG.md Updates
- Fill out very brief/short bullet points of what was changed, fixed, added, in the CHANGELOG.md file
- Update CHANGELOG.md when making significant changes to the codebase

## CSV Format

The application imports data from two CSV formats:

1. **Player Roster CSV**: player_name, jersey_number, position, height, weight, year
2. **Game Statistics CSV**: Complex format with shot strings per quarter
   - Shot string format: "XY-Z" where X=made shots, Y=shot type (2/3), Z=FT result

See `docs/design_doc.md` for detailed CSV specifications.

## Docker Development

The project includes Docker support for consistent development:
- `docker-compose.yml`: Defines PostgreSQL and app services
- `Dockerfile`: Multi-stage build for production deployment
- Use `make shell` to access the container's bash shell

## Important Production Database Notes

**Production = Cloud Run + Cloud SQL PostgreSQL**
- The web UI at https://league-stats.net uses a Cloud SQL PostgreSQL instance
- Database migrations are automatically run via GitHub Actions on each deployment
- For manual migrations: `make migrate-production`
- Cloud SQL instance: `basketball-stats-db` in region `us-west1`
- Duplicate games are prevented by a unique constraint on (date, playing_team_id, opponent_team_id)
- Jersey numbers are stored as strings to handle variations like "0" vs "00"

**Database Migration Process**:
1. **Automated** (recommended): Push to main branch triggers GitHub Actions → builds image → **runs migrations FIRST** → deploys (only if migrations succeed)
2. **Manual**: Use `make migrate-production` to run migrations immediately
3. **Monitoring**: Use `make migration-logs` and `make migration-status` to monitor migration progress

**Migration Strategy**: Pre-deployment migrations for maximum safety - if migrations fail, deployment stops and old code continues running.

## Infrastructure Management

### Terraform Cloud Configuration
**Important: All infrastructure is managed via Terraform Cloud**
- **Organization**: deck15
- **Workspace**: gcp-infra-basketball-stats
- **Backend**: Remote execution in Terraform Cloud
- **Authentication Required**: Run `terraform login` before any terraform operations

### Infrastructure Commands
```bash
# Infrastructure is in the infra/ directory
cd infra

# Authenticate with Terraform Cloud (required before any operations)
terraform login

# Run terraform commands via Makefile
make init    # Initialize terraform
make plan    # Review planned changes
make apply   # Apply infrastructure changes
make destroy # Destroy infrastructure (use with caution)
```

### GCP Infrastructure Components
- **Project ID**: basketball-stats-461220
- **Region**: us-west1
- **Primary Services**:
  - Cloud Run (serverless container hosting)
  - Cloud SQL PostgreSQL (managed database)
  - Cloud DNS (domain management)
  - Artifact Registry (container images)
  - Google OAuth 2.0 (authentication)

### Domain & DNS
- **Domain**: league-stats.net
- **DNS Provider**: Google Cloud DNS (authoritative)
- **Nameservers**: ns-cloud-d[1-4].googledomains.com
- **SSL**: Automatic via Google Cloud Run
- **URL**: https://basketball-stats-480880014651.us-west1.run.app (always accessible)
- **Custom Domain**: https://league-stats.net (after SSL provisioning)

### Domain Management
**Important**: Domain mapping is managed outside of Terraform due to ownership requirements.

**Required Steps**:
1. Verify domain in Google Search Console (already done ✓)
2. Create domain mapping with domain owner account:
   ```bash
   gcloud beta run domain-mappings create \
     --service=basketball-stats \
     --domain=league-stats.net \
     --region=us-west1 \
     --project=basketball-stats-461220
   ```
3. Wait for SSL certificate (15 min - 24 hours)
4. Check status:
   ```bash
   gcloud beta run domain-mappings describe \
     --domain=league-stats.net \
     --region=us-west1
   ```

**Why not in Terraform?**: Cloud Run domain mappings require personal Google account domain ownership verification, which service accounts cannot provide.

**Cost Optimization**: Using Cloud Run's built-in domain mapping (free) instead of Load Balancer (~$18/month). App runs at root domain (league-stats.net).

## Coding Principles
- **Core Principles**: Follow SOLID/DRY/KISS/YAGNI principles
- **Code Style**: Python 3.11+, ruff for formatting/linting, strict type hints
- **Database**: SQLAlchemy ORM, parameterized queries only (never raw f-strings)
- **Validation**: Pydantic V2 for all validation & settings
- **Logging**: Use `logging` module, never `print()` statements
- **Security**: No secrets in code, load via `config.py` from `.env`
- **File Format**: Always use LF line endings (not CRLF) when writing files
- **Documentation**: Document _why_, not _what_ - concise Google-style docstrings
- **Error Handling**: Fail fast & loudly - explicit exceptions over silent `None`s
- **Design**: Small units with single purpose, prefer pure functions over classes unless stateful behavior needed
- **CSV Configuration**: Shot-string legend and CSV layout are defined in `app/config.py`
```
