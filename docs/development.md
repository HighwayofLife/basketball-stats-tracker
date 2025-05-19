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

1. Build and start containers:
   ```bash
   make run
   ```

2. Stop containers when done:
   ```bash
   make stop
   ```

## Database Management

### CLI Commands (Recommended for All Environments)

```bash
# Initialize or update database schema
basketball-stats init-db

# Initialize database with force option (resets all data)
basketball-stats init-db --force

# Create a new migration for schema changes
basketball-stats init-db --migration

# Seed database with development data
basketball-stats seed-db

# Check database connectivity
basketball-stats health-check
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

Run all tests:
```bash
make test
```

Run tests with coverage reporting:
```bash
make test-coverage
```

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
basketball-stats import-roster --roster-file players_template.csv

# Preview changes without modifying the database
basketball-stats import-roster --roster-file players_template.csv --dry-run
```

Import game statistics:
```bash
# Basic usage
basketball-stats import-game --game-stats-file game_stats_template.csv

# Preview changes without modifying the database
basketball-stats import-game --game-stats-file game_stats_template.csv --dry-run
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
basketball-stats report --game-id 1

# CSV output
basketball-stats report --game-id 1 --format csv
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

## Further Documentation

For design details and development roadmap, see:
- [Design Document](design_doc.md)
- [Development Phases](development_phases.md)
