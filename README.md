# Python Basketball Stats Tracker

A simple web application for tracking basketball game statistics for a small league. Features include:
- Web UI for entering game and player stats
- Persistent storage using SQLite and SQLAlchemy
- Data validation with Pydantic
- Game summary reports via CLI or CSV export
- Roster management via CSV import

## Setup Instructions

### Prerequisites

- Python 3.11 or higher
- Make (optional, for using Makefile commands)
- Docker and Docker Compose (optional, for containerized setup)

### Local Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/highwayoflife/league-stats.git
   cd league-stats
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

4. Initialize the database with Alembic migrations:
   ```bash
   # Using make (recommended)
   make local-init-db
   
   # Or directly with the CLI
   python run_cli.py init-db
   ```

5. (Optional) Seed the database with development data:
   ```bash
   make local-seed-db
   ```

6. Import your league's roster from a CSV file:
   ```bash
   # Using provided template as an example
   python -m app.cli import-roster --roster-file players_template.csv
   
   # Use dry run mode to preview changes without modifying the database
   python -m app.cli import-roster --roster-file your_roster.csv --dry-run
   ```

   The CSV file must include these columns:
   - `team_name`: The name of the team
   - `player_name`: The player's full name
   - `jersey_number`: The player's jersey number (integer)

### Docker Setup

1. Build and start containers:
   ```bash
   make run
   ```

2. Initialize the database:
   ```bash
   make init-db
   ```

3. Stop containers when done:
   ```bash
   make stop
   ```

## Available Commands

Run `make help` to see all available commands. Key commands include:

### Database Management

#### Local Development
- `make local-init-db` - Apply Alembic migrations to update the database schema
- `make local-reset-db` - Reset the database, destroying all data
- `make local-make-migration` - Create a new Alembic migration based on model changes
- `make local-seed-db` - Seed the database with sample data for development
- `make local-db-health` - Check database connectivity

#### Docker Environment
- `make init-db` - Apply Alembic migrations to update the database schema
- `make reset-db` - Reset the database, destroying all data
- `make make-migration` - Create a new Alembic migration based on model changes
- `make seed-db` - Seed the database with sample data for development
- `make db-health` - Check database connectivity

## Development

See the documentation in the `docs/` directory for design details and development phases.