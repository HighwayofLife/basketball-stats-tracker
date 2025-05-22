# Basketball Stats Tracker - Developer Guide

This document provides detailed instructions for development and database management for the Basketball Stats Tracker application.

## Development Setup

### Local Development Environment

1. Clone the repository:
   ```bash
   git clone https://github.com/highwayoflife/basketball-stats-tracker.git
   cd basketball-stats-tracker
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -e .
   ```

### Docker Development Environment

#### Using Docker Compose (Recommended for Development)

Docker Compose provides a complete development environment with a PostgreSQL database:

1. Build and start containers:
   ```bash
   # Build and run with docker-compose
   make run
   ```

2. Check logs:
   ```bash
   # Follow the logs
   make logs
   ```

3. Access a shell in the container:
   ```bash
   # Open a shell for running commands
   make shell
   ```

4. Stop containers when done:
   ```bash
   # Stop the containers
   make stop
   ```

#### Using Standalone Docker (Simpler, SQLite-based)

For a simpler environment with the built-in SQLite database:

1. Build the production image:
   ```bash
   make docker-build
   ```

2. Run a standalone container:
   ```bash
   make docker-run
   ```

3. Clean up resources:
   ```bash
   # Remove Docker containers and images
   make docker-clean
   ```

#### Common Docker Commands

| Command | Description |
|---------|-------------|
| `make run` | Build and run with docker-compose |
| `make stop` | Stop docker-compose containers |
| `make logs` | View logs from containers |
| `make shell` | Open a shell in the web container |
| `make docker-build` | Build standalone Docker image |
| `make docker-run` | Run standalone Docker container |
| `make docker-clean` | Clean up Docker resources |
| `make docker-compose-build` | Build images with docker-compose |

## Docker Architecture

The Basketball Stats Tracker application uses Docker for both development and production environments.

### Docker Implementation

#### Multi-Stage Dockerfile

The project uses a multi-stage build process in the root `Dockerfile`:

1. **Builder Stage**:
   - Uses Python 3.11 slim as the base
   - Installs build dependencies
   - Prepares Python packages

2. **Final Stage**:
   - Uses a minimal Python 3.11 slim image
   - Copies only necessary dependencies from the builder stage
   - Runs with a non-root user for security
   - Uses uvicorn directly for optimal performance

#### Development with Docker Compose

The `docker-compose.yml` file provides a complete development environment:

- **PostgreSQL Database**: Runs in a separate container
- **Web Application**: Built from the same Dockerfile
- **Volume Mounts**: For live code changes without rebuilding
- **Health Checks**: Ensures dependencies are ready before starting the app

### Docker vs. Local Development

Both environments have their advantages:

| Feature | Docker | Local |
|---------|--------|-------|
| Setup Difficulty | Easier (just Docker required) | More involved (Python, venv, etc.) |
| Database | PostgreSQL (production-like) | SQLite (simpler) |
| Isolation | Complete environment isolation | Depends on local setup |
| Performance | Slightly slower | Native speed |
| Resource Usage | Higher (Docker overhead) | Lower |

Choose the approach that best fits your workflow and system resources.

## Database Management

### First-Time Setup (Important!)

When setting up the project for the first time or after a clean, you **must** initialize the database with migrations:

```bash
# Create an initial migration AND apply it
python -m app.cli init-db --migration
```

Without this step, the database will have no tables and commands like `import-game` will fail with an error like "no such table: teams".

You can also use the Makefile command:
```bash
make local-first-time-setup
```

#### Recommended Workflow for New Developers

1. Clone the repository
2. Create and activate virtual environment: `python -m venv venv && source venv/bin/activate`
3. Install dependencies: `pip install -e .`
4. Initialize database with migrations: `make local-first-time-setup`
5. Import example data: `basketball-stats import-game --file game_stats_template.csv`
6. Run tests to verify setup: `pytest`

### Regular CLI Commands

```bash
# Initialize or update database schema with existing migrations
python -m app.cli init-db

# Initialize database with force option (resets all data)
python -m app.cli init-db --force

# Create a new migration for schema changes
python -m app.cli init-db --migration

# Check database health
python -m app.cli health-check
```

### Troubleshooting Database Issues

If you encounter errors like "no such table" when running commands, check:

1. Verify the database has tables:
   ```bash
   sqlite3 data/league_stats.db ".tables"
   ```

2. If only `alembic_version` exists but no application tables, you need to create migrations:
   ```bash
   python -m app.cli init-db --migration
   ```

3. If you want to start fresh:
   ```bash
   python -m app.cli init-db --force
   ```

4. Common error messages and solutions:

   - **"Error: No such file or directory: 'data/league_stats.db'"**:
     The `data` directory doesn't exist or the database hasn't been created.
     ```bash
     mkdir -p data
     python -m app.cli init-db --migration
     ```

   - **"Error: no such table: teams"**:
     Database exists but tables haven't been created.
     ```bash
     python -m app.cli init-db --migration
     ```

   - **"Error: UNIQUE constraint failed"**:
     You're trying to import data that conflicts with existing records.
     ```bash
     python -m app.cli init-db --force  # Warning: Deletes all data
     ```

   - **"No such module 'fastapi'"**:
     Missing dependencies for the MCP server.
     ```bash
     pip install fastapi uvicorn
     ```

# Seed database with development data
basketball-stats seed-db

# Check database connectivity
basketball-stats health-check

# Start the MCP server for SQL and NL queries
basketball-stats mcp-server
```

### Make Commands (For Development Convenience)

#### Local Environment

- `make local-init-db` - Apply Alembic migrations to update the database schema
- `make local-reset-db` - Reset the database, destroying all data
- `make local-init-db-migration` - Create a new Alembic migration based on model changes
- `make local-seed-db` - Seed the database with sample data for development
- `make local-db-health` - Check database connectivity

#### Docker Environment

- `make init-db` - Apply Alembic migrations to update the database schema
- `make reset-db` - Reset the database, destroying all data
- `make init-db-migration` - Create a new Alembic migration based on model changes
- `make seed-db` - Seed the database with sample data for development
- `make db-health` - Check database connectivity

## Testing

### Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run only unit tests
python -m pytest tests/unit/

# Run only integration tests
python -m pytest tests/integration/

# Run tests with verbose output
python -m pytest tests/ -v

# Run a specific test file
python -m pytest tests/integration/test_import_game_command.py

# Run tests with coverage reporting
python -m pytest --cov=app --cov-report=term tests/
```

### Test Structure

1. **Unit Tests**: Located in `tests/unit/`, test individual components in isolation
2. **Integration Tests**: Located in `tests/integration/`, test multiple components working together
3. **Test Fixtures**: Common test setup code is in `tests/conftest.py`

### Testing Best Practices

1. **Database Tests**: Use the `db_session` fixture for database operations
2. **CLI Tests**: Use the `cli_runner` fixture for testing CLI commands
3. **Patching External Services**: Use `monkeypatch` to replace services like the database manager

### Example: Testing CSV Import

To test the `import-game` command, we:
1. Create a test database in memory
2. Mock the database session to use our test session
3. Run the CLI command with a sample CSV file
4. Verify the database contains the expected data

```python
def test_import_game_template(cli_runner, template_csv_path, db_session, monkeypatch):
    """Test importing the game_stats_template.csv file via the CLI."""
    # Mock the db_manager to use our test session
    @contextmanager
    def mock_get_db_session():
        try:
            yield db_session
        finally:
            pass

    # Apply the monkeypatch
    import app.data_access.database_manager
    monkeypatch.setattr(app.data_access.database_manager.db_manager,
                       "get_db_session", mock_get_db_session)

    # Run the CLI command
    result = cli_runner.invoke(cli, ["import-game", "--file", template_csv_path])

    # Verify results
    assert result.exit_code == 0
    assert "Import completed successfully" in result.stdout
```

### Running Tests with VSCode

VS Code provides a convenient interface for running and debugging tests:

1. **Test Explorer**: Access it by clicking the flask icon in the sidebar
2. **Run Tests**: Click the play button next to any test or test file
3. **Debug Tests**: Click the debug icon next to any test to run with debugger
4. **Filter Tests**: Use the search box to find specific tests
5. **View Output**: Test results appear directly in the Test Explorer

### Debug Configurations

The project includes several VS Code debug configurations:

1. **Python: Current File** - Run the currently open file
2. **Python: All Tests** - Run all tests with the debugger
3. **Python: Unit Tests** - Run only unit tests
4. **Python: Integration Tests** - Run only integration tests
5. **Python: Import Game Data** - Run the import game command
6. **Python: Debug MCP Server** - Run the MCP server in debug mode

To use these configurations:
1. Open the Run and Debug panel (Ctrl+Shift+D or Cmd+Shift+D)
2. Select a configuration from the dropdown
3. Click the green play button or press F5

## Project Structure

```
basketball_stats_tracker/
├── app/
│   ├── cli.py                # CLI commands definition
│   ├── config.py             # Application configuration, including shot mapping
│   ├── data_access/          # Database access layer
│   │   ├── crud/             # CRUD operations
│   │   ├── database_manager.py
│   │   └── models.py         # SQLAlchemy ORM models
│   ├── reports/              # Reporting modules
│   ├── schemas/              # Pydantic models for data validation
│   ├── services/             # Business logic services
│   ├── utils/                # Utility functions
│   └── web_ui/               # Flask routes and templates (future)
├── data/                     # SQLite database location
├── docs/                     # Documentation
├── migrations/               # Alembic migration files
└── tests/                    # Test files
```

## CLI Commands

The application is designed to be used primarily through CLI commands rather than Make targets, though Make targets exist for development convenience.

### Data Import

Import team rosters:
```bash
# Basic usage
basketball-stats import-roster --file players_template.csv
# Or with short option:
basketball-stats import-roster -f players_template.csv

# Preview changes without modifying the database
basketball-stats import-roster -f players_template.csv --dry-run
```

Import game statistics:
```bash
# Basic usage
basketball-stats import-game --file game_stats_template.csv
# Or with short option:
basketball-stats import-game -f game_stats_template.csv

# Preview changes without modifying the database
basketball-stats import-game -f game_stats_template.csv --dry-run
```

### Database Management

```bash
# Initialize or upgrade database schema
basketball-stats init-db

# Check database health
basketball-stats health-check

# Seed database with sample data
basketball-stats seed-db
```

### Report Generation

Generate box score reports:
```bash
# Console output (default)
basketball-stats report --id 1

# CSV output
basketball-stats report --id 1 --format csv

# CSV output with custom filename
basketball-stats report --id 1 --format csv --output report.csv
```

## Available Make Commands

While CLI commands are preferred for end-users, developers can use Make commands for convenience. Run `make help` to see all available commands in the project's Makefile.

## Building the Standalone Executable

You can create a standalone executable using PyInstaller, which will bundle the application and all its dependencies into a single package that can be run without Python installed.

### Prerequisites for Building

- Python 3.11 or higher
- PyInstaller (installed automatically by the build process)

### Building Process

1. Install build dependencies:
   ```bash
   pip install -e ".[build]"
   ```

2. Using the make command:
   ```bash
   make bundle
   ```

   Or manually:
   ```bash
   chmod +x build_standalone.sh
   ./build_standalone.sh
   ```

3. The build process will:
   - Detect your operating system
   - Build the executable with PyInstaller
   - Create a ZIP archive for distribution
   - Output results to the `dist/` directory

The output includes:
- `dist/basketball-stats/` - Directory containing the executable and all required files
- `dist/basketball-stats-{OS}.zip` - ZIP archive ready for distribution

### Build Configuration

The PyInstaller build is configured in:
- `basketball_stats.spec` - Main PyInstaller specification file
- `hooks/pyinstaller_hook.py` - Runtime adjustments for bundled app
- `bundle_app.py` - Entry point for the bundled application

For more details on the PyInstaller bundling process, see [PyInstaller Bundle Documentation](pyinstaller_bundle.md).

### Distributing the Executable

1. Share the ZIP archive with users
2. Users can extract the ZIP and run the application without installing Python:
   - Windows: double-click `start.bat` or `basketball-stats.exe`
   - macOS/Linux: `./start.sh` or `./basketball-stats`

## Model Context Protocol (MCP) Server

The application includes an MCP server that provides SQL and natural language access to the basketball stats database via an HTTP API.

### Starting the Server

```bash
# Start the MCP server
python -m app.cli mcp-server
```

The server will start on http://localhost:8000 by default.

### API Endpoints

1. **SQL Query**: `POST /api/query`
   - Execute a SQL query against the database
   - Request body: `{ "query": "SELECT * FROM teams", "parameters": {} }`

2. **Natural Language Query**: `POST /api/nl_query`
   - Process a natural language question
   - Request body: `{ "query": "Show me all teams" }`

3. **List Tables**: `GET /api/tables`
   - Get a list of all tables in the database

4. **Table Schema**: `GET /api/schema/{table}`
   - Get the schema for a specific table

5. **Health Check**: `GET /api/health`
   - Check if the server and database are healthy

### Example Queries

1. **SQL Query**:
   ```bash
   curl -X POST http://localhost:8000/api/query \
     -H "Content-Type: application/json" \
     -d '{"query": "SELECT * FROM players"}'
   ```

2. **Natural Language Query**:
   ```bash
   curl -X POST http://localhost:8000/api/nl_query \
     -H "Content-Type: application/json" \
     -d '{"query": "Show me player stats for Player One"}'
   ```

3. **Table Schema**:
   ```bash
   curl http://localhost:8000/api/schema/teams
   ```

### Using with VSCode Copilot

The MCP server can be used with VSCode Copilot to provide natural language queries over your basketball stats data. Set up:

1. Start the server: `python -m app.cli mcp-server`
2. Configure Copilot to use the MCP endpoint at http://localhost:8000
3. Ask questions like "Show me all teams in the database" or "Get stats for Player One"

## VSCode Integration

The project includes VSCode configurations for easier development and testing.

### Running Tests in VSCode

1. Install the Python extension for VSCode
2. Open the Testing panel (flask icon in the sidebar)
3. Click the "Play" button to run all tests
4. Hover over individual tests to run them specifically

### Debug Configurations

The following debug configurations are available (F5 or Run → Start Debugging):

1. **Python: Current File** - Run and debug the currently open file
2. **Python: All Tests** - Run all tests with the debugger
3. **Python: Unit Tests** - Run only unit tests
4. **Python: Integration Tests** - Run only integration tests
5. **Python: Current Test File** - Run tests in the currently open file
6. **Python: Debug MCP Server** - Start the MCP server in debug mode

### Shortcuts

1. Run a single test: Click the "Play" button next to the test function
2. Debug a single test: Click the "Debug" button next to the test function
3. Set breakpoints: Click in the margin to the left of a line number
4. Step through code: Use the debug controls in the floating debug toolbar

### Recommended Extensions

1. **Python** - Microsoft's Python extension
2. **Pylance** - Microsoft's Python language server
3. **Python Test Explorer** - Better test discovery and execution UI
4. **Black Formatter** - Auto-format code on save
5. **Ruff** - Fast Python linter

## Further Documentation

For design details and development roadmap, see:
- [Design Document](design_doc.md)
- [Development Phases](development_phases.md)
