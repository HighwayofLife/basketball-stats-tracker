# Python Basketball Stats Tracker

A simple application for tracking basketball game statistics for a small league. This application allows for easy data entry via CSV files and generates statistical reports for games and players.

## Features

- Game and player stats import via CSV files
- Game summary reports via CLI or CSV export
- Roster management via CSV import
- Configurable shot string parsing for flexible data entry
- Team and player performance statistics
- Standalone executable available (no Python installation required)

## Quick Start

Choose the option that works best for you:

1. **Standalone Application** - Download and run, no installation required
2. **Python Package** - If you already use Python

### Installation

Using pip:

```bash
# Install from PyPI
pip install basketball-stats-tracker

# Initialize the database
basketball-stats init-db

# Optional: Add sample data
basketball-stats seed-db
```

That's it! The application is ready to use.

> **Note:** For Docker setup or development environment instructions, see the [Developer Guide](docs/development.md).

## Installation Options

### Option 1: Standalone Executable (Recommended for Most Users)

No Python installation required! Just download and run:

1. Download the latest release for your OS from the [Releases page](https://github.com/highwayoflife/basketball-stats-tracker/releases)
2. Extract the ZIP file
3. Run the application:
   - **Windows**: Double-click `start.bat` or run `basketball-stats.exe`
   - **macOS**: Use `./start.sh` or `./basketball-stats` in Terminal
   - **Linux**: Use `./start.sh` or `./basketball-stats` in terminal

### Option 2: Python Package

If you already use Python (version 3.11+):

```bash
# Install from PyPI
pip install basketball-stats-tracker

# Initialize the database
basketball-stats init-db
```

## Using the Application

### Importing Team Rosters

Import your league's roster from a CSV file:
```bash
basketball-stats import-roster --file players_template.csv
# Or simply with the short option:
basketball-stats import-roster -f players_template.csv
```

To preview changes without modifying the database:
```bash
basketball-stats import-roster -f players_template.csv --dry-run
```

The roster CSV file must include these columns:
- `team_name`: The name of the team
- `player_name`: The player's full name
- `jersey_number`: The player's jersey number (integer)

Example structure (`players_template.csv`):
```
team_name,player_name,jersey_number
Warriors,Stephen Curry,30
Warriors,Klay Thompson,11
Lakers,LeBron James,23
```

### Importing Game Statistics

Import game statistics from a CSV file:
```bash
basketball-stats import-game --file game_stats_template.csv
# Or simply with the short option:
basketball-stats import-game -f game_stats_template.csv
```

To preview changes without modifying the database:
```bash
basketball-stats import-game -f game_stats_template.csv --dry-run
```

The game statistics CSV file should have the following structure:
1. Game information rows (Playing Team, Opponent Team, Date)
2. Player statistics rows with the `PLAYER_DATA` prefix

Example structure (`game_stats_template.csv`):
```
GAME_INFO_KEY,VALUE
Playing Team,Team A
Opponent Team,Team B
Date,2025-05-15
PLAYER_STATS_HEADER,Team Name,Player Jersey,Player Name,Fouls,QT1 Shots,QT2 Shots,QT3 Shots,QT4 Shots
PLAYER_DATA,Team A,10,Player One,2,22-1x,3/2,11,
PLAYER_DATA,Team A,23,Player Two,3,12,x,-/,22
```

#### Shot String Format

The shot strings represent made/missed shots using the following characters:
- `1` = made free throw (FT)
- `x` = missed free throw
- `2` = made 2-point field goal
- `-` = missed 2-point field goal
- `3` = made 3-point field goal
- `/` = missed 3-point field goal

For example, the shot string `22-1x/` represents:
- Two made 2-point shots (`22`)
- One missed 2-point shot (`-`)
- One made free throw (`1`)
- One missed free throw (`x`)
- One missed 3-point shot (`/`)

### Generating Reports

Generate box score reports for games:
```bash
# Console output (default)
basketball-stats report --id 1
# Or with the short option:
basketball-stats report -i 1

# CSV output with default filename (game_1_box_score.csv)
basketball-stats report -i 1 --format csv

# CSV output with custom filename
basketball-stats report -i 1 -f csv -o my_report.csv
```

The report includes:
- Individual player statistics (points, shooting percentages, etc.)
- Team totals and shooting percentages
- Game summary information

## Documentation

For more detailed information, please consult:

- [Developer Guide](docs/development.md) - For development setup, database management, and CLI commands
- [Design Document](docs/design_doc.md) - Technical design and architecture details
- [Development Phases](docs/development_phases.md) - Project implementation roadmap

## For Developers

If you're interested in contributing to the project or building the standalone executable yourself, please see the [Developer Guide](docs/development.md) for detailed instructions on:

- Setting up a development environment
- Running tests
- Building the standalone executable
- Project architecture

The developer documentation also contains information about the [PyInstaller bundling process](docs/pyinstaller_bundle.md) used to create the standalone executables.