BASKETBALL STATS TRACKER
=====================

This is a standalone application for tracking basketball game statistics.
No installation of Python, pip, or Docker is required.

Getting Started
--------------

1. Run the basketball-stats executable:
   - Windows: double-click basketball-stats.exe or run from command prompt
   - macOS/Linux: ./basketball-stats in terminal

2. The database will be automatically initialized in the data/ directory 
   (created in the same folder as the executable).

Available Commands
-----------------

All commands are available by running:
./basketball-stats [command]

Main commands:

- init-db              Initialize or upgrade the database schema
- import-roster        Import teams and players from a CSV file
- import-game          Import game statistics from a CSV file
- report               Generate a box score report for a specific game
- health-check         Check if the database is properly set up and accessible
- seed-db              Seed the database with sample data

For help on any command:
./basketball-stats [command] --help

Example usage:
./basketball-stats import-roster --roster-file players_template.csv
./basketball-stats import-game --game-stats-file game_stats_template.csv
./basketball-stats report --game-id 1

CSV File Templates
-----------------
Example CSV files are included in this package:
- players_template.csv - Template for importing team rosters
- game_stats_template.csv - Template for importing game statistics

For more information, see the full documentation at:
https://github.com/highwayoflife/basketball-stats-tracker
