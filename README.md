# Python Basketball Stats Tracker

A simple application for tracking basketball game statistics for a small league. This application allows for easy data entry via CSV files and generates statistical reports for games and players.

## Features

- Game and player stats import via CSV files
- Game summary reports via CLI or CSV export
- Roster management via CSV import
- Configurable shot string parsing for flexible data entry
- Team and player performance statistics

## Quick Start

### Prerequisites

- Python 3.11 or higher
- Docker and Docker Compose (optional, for containerized setup)

### Installation

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

4. Initialize the database:
   ```bash
   basketball-stats init-db
   ```

5. (Optional) Seed the database with sample data:
   ```bash
   basketball-stats seed-db
   ```

> **Note:** For Docker setup or development environment instructions, see the [Developer Guide](docs/development.md).

## Using the Application

### Importing Team Rosters

Import your league's roster from a CSV file:
```bash
basketball-stats import-roster --roster-file players_template.csv
```

To preview changes without modifying the database:
```bash
basketball-stats import-roster --roster-file players_template.csv --dry-run
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
basketball-stats import-game --game-stats-file game_stats_template.csv
```

To preview changes without modifying the database:
```bash
basketball-stats import-game --game-stats-file game_stats_template.csv --dry-run
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
basketball-stats report --game-id 1

# CSV output
basketball-stats report --game-id 1 --format csv
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