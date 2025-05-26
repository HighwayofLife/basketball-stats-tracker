# **Technical Design Document: Python Basketball Stats Tracker**

**1. Introduction**

* 1.1. Purpose:
  To develop a simple Python application for tracking basketball game statistics for a small league. The application will allow users to input game details, individual player performance per quarter (fouls and a simplified shot string) via **a CSV file import mechanism**, store this data persistently using SQLAlchemy, validate data with Pydantic v2, and generate game summary reports.
* **1.2. Goals:**
  * **Simplicity (KISS):** Focus on core functionality, straightforward data structures, and a simple **CSV import** for data entry. Avoid over-engineering.
  * **Maintainability (SOLID):** Structure the application with clear separation of concerns.
  * **Efficient Data Entry:** Allow for quick input of game stats via a structured **CSV file**.
  * **Accurate Storage:** Persistently store raw makes and attempts for Free Throws (FT), 2-Point Field Goals (2P), and 3-Point Field Goals (3P) by quarter for each player.
  * **Basic Reporting:** Output game statistics in a clear tabular format or as a CSV file.
* **1.3. Scope:**
  * **Input:** Game information (teams, date), player fouls, and per-quarter shot strings for each player, **imported from a CSV file**. Data validation using Pydantic v2.
  * **Storage:** SQLite database with SQLAlchemy as the ORM.
  * **Processing:** Parsing shot strings into makes/attempts per quarter, aggregating for game totals.
  * **Output:** Game box score table.
  * **Initial Version:** Focus on data entry via **CSV import, processed by a command-line script invoked via `make` targets**.

**2. System Architecture**

The application will follow a layered architecture:

* **2.1. Input Layer (CSV Import & CLI):**
  * Data entry will be performed by preparing a CSV file with a specific format (detailed in Section 5).
  * **CLI commands, defined in `app/cli.py` (and run directly as `basketball-stats ...`), will be responsible for processing these files. These commands prioritize simplicity and user-friendliness (e.g., `basketball-stats import-game` instead of longer alternatives).**
    *   Reading the CSV file.
    *   Validating the structure and content of the CSV data using Pydantic models (defined in `app/web_ui/schemas.py` or a dedicated `app/schemas/csv_schemas.py`).
    *   Passing the validated data to the service layer for processing and storage.
  * While a web UI (Flask) might exist for other purposes (e.g., viewing reports), primary data entry is through CSV. The `app/main.py`, `app/web_ui/routes.py`, and `app/web_ui/templates/` directory will be initially focused on report display or deferred. Pydantic models for CSV data validation will be crucial.
* **2.2. Service Layer (Business Logic - `app/services/`):**
  * Contains the core application logic.
  * Coordinates interactions between the CSV import process (triggered by a `make` target) and the Data Access Layer.
* **2.3. Data Access Layer (DAL - `app/data_access/`):**
  * Encapsulates all database interactions using SQLAlchemy.
  * Defines SQLAlchemy models for database tables.
  * Provides an API for the service layer to interact with the database, with CRUD operations organized per model.
  * Files: `app/data_access/database_manager.py` (handles SQLAlchemy engine and session setup), `app/data_access/models.py` (SQLAlchemy model definitions), and `app/data_access/crud/` (directory containing CRUD operations specific to each model, e.g., `crud_team.py`).
* **2.4. Utility Layer (`app/utils/`):**
  * `input_parser.py`: Parses quarter shot strings **based on a configurable character mapping defined in `app/config.py`**.
  * `stats_calculator.py`: Calculates derived statistics.
* **2.5. Database:**
  * SQLite (`data/league_stats.db`) accessed via SQLAlchemy.
* **2.6. Containerization:**
  * **Multi-stage Docker Build:**
    * Builder stage for compilation and dependency installation
    * Final stage with minimal runtime dependencies
    * Non-root user for security
    * Direct uvicorn execution for optimal performance
  * **Development Environment:**
    * Docker Compose for local development
    * Hot-reload enabled for faster development
    * Volume mounts for code changes
  * **Production Environment:**
    * Optimized single container deployment
    * Environment variable configuration
    * Proper security practices (non-root user, minimal dependencies)

**3. File Layout**

```
basketball_stats_tracker/
├── Dockerfile             # Multi-stage production Docker build
├── docker-compose.yml     # Development environment setup
├── Makefile              # Build and deployment automation
├── app/
│   ├── cli.py                # Defines CLI commands (e.g., for DB setup, CSV import, report generation), invoked via 'basketball-stats' entry point, typically run using 'make' targets.
│   ├── main.py               # Flask app initialization (potentially for future UI/report display)
│   ├── config.py             # Application configuration, **including shot string character mapping.**
│   │
│   ├── web_ui/               # Potentially for report display UI in the future
│   │   ├── routes.py         # Flask Blueprint with route definitions (if web UI is used for reports)
│   │   ├── templates/        # HTML templates (if web UI is used for reports)
│   │   │   └── ...
│   │   └── schemas.py        # Pydantic models for data validation (used by CSV import and potentially future web UI)
│   │
│   ├── services/
│   │   ├── game_service.py
│   │   ├── player_service.py
│   │   └── stats_entry_service.py
│   │
│   ├── data_access/
│   │   ├── database_manager.py # SQLAlchemy setup, session management
│   │   ├── models.py         # SQLAlchemy ORM models
│   │   └── crud/             # Directory for CRUD operations per model
│   │       ├── crud_team.py
│   │       ├── crud_player.py
│   │       └── ...           # etc.
│   │
│   ├── utils/
│   │   ├── input_parser.py   # Parses quarter shot strings
│   │   └── stats_calculator.py
│   │
│   └── reports/
│       └── report_generator.py # Generates output tables/CSVs
│
├── data/                     # Directory to store the SQLite database file
│   └── league_stats.db
│
├── tests/                    # Directory for unit/integration tests
│   ├── test_input_parser.py
│   └── test_stats_calculator.py
│
├── pyproject.toml            # Project metadata and dependencies
└── README.md                 # Project overview and setup instructions
```

**4. Data Model (Database Schema - SQLAlchemy ORM Models)**

*(This section remains unchanged from the previous version where SQLAlchemy models were introduced: Team, Player, Game, PlayerGameStats, PlayerQuarterStats models as defined in `app/data_access/models.py`.)*

* **4.1. Team Model (corresponds to Teams Table)**
  * id (Integer, primary_key=True, autoincrement=True)
  * name (String, unique=True, nullable=False)
  * players (relationship backref to Player)
  * home_games (relationship backref to Game where team is playing_team)
  * away_games (relationship backref to Game where team is opponent_team)
* **4.2. Player Model (corresponds to Players Table)**
  * id (Integer, primary_key=True, autoincrement=True)
  * team_id (Integer, ForeignKey('teams.id'), nullable=False)
  * name (String, nullable=False)
  * jersey_number (Integer, nullable=False)
  * team (relationship to Team)
  * game_stats (relationship backref to PlayerGameStats)
  * UniqueConstraint('team_id', 'jersey_number', name='uq_player_team_jersey')
  * UniqueConstraint('team_id', 'name', name='uq_player_team_name')
* **4.3. Game Model (corresponds to Games Table)**
  * id (Integer, primary_key=True, autoincrement=True)
  * date (String, nullable=False) *(Store as YYYY-MM-DD string or use SQLAlchemy Date type)*
  * playing_team_id (Integer, ForeignKey('teams.id'), nullable=False)
  * opponent_team_id (Integer, ForeignKey('teams.id'), nullable=False)
  * playing_team (relationship to Team, foreign_keys=[playing_team_id])
  * opponent_team (relationship to Team, foreign_keys=[opponent_team_id])
  * player_game_stats (relationship backref to PlayerGameStats)
* **4.4. PlayerGameStats Model (corresponds to PlayerGameStats Table)**
  * id (Integer, primary_key=True, autoincrement=True)
  * game_id (Integer, ForeignKey('games.id'), nullable=False)
  * player_id (Integer, ForeignKey('players.id'), nullable=False)
  * fouls (Integer, nullable=False, default=0)
  * total_ftm (Integer, nullable=False, default=0)
  * total_fta (Integer, nullable=False, default=0)
  * total_2pm (Integer, nullable=False, default=0)
  * total_2pa (Integer, nullable=False, default=0)
  * total_3pm (Integer, nullable=False, default=0)
  * total_3pa (Integer, nullable=False, default=0)
  * game (relationship to Game)
  * player (relationship to Player)
  * quarter_stats (relationship backref to PlayerQuarterStats)
  * UniqueConstraint('game_id', 'player_id', name='uq_player_game')
* **4.5. PlayerQuarterStats Model (corresponds to PlayerQuarterStats Table)**
  * id (Integer, primary_key=True, autoincrement=True)
  * player_game_stat_id (Integer, ForeignKey('player_game_stats.id'), nullable=False)
  * quarter_number (Integer, nullable=False) # Add CheckConstraint in SQLAlchemy
  * ftm (Integer, nullable=False, default=0)
  * fta (Integer, nullable=False, default=0)
  * fg2m (Integer, nullable=False, default=0)
  * fg2a (Integer, nullable=False, default=0)
  * fg3m (Integer, nullable=False, default=0)
  * fg3a (Integer, nullable=False, default=0)
  * player_game_stat (relationship to PlayerGameStats)
  * UniqueConstraint('player_game_stat_id', 'quarter_number', name='uq_player_game_quarter')
  * CheckConstraint('quarter_number >= 1 AND quarter_number <= 4', name='check_quarter_number')

**5. Input Mechanism & Data Processing**

Data will be imported into the system via a CSV file. This CSV file will contain game information and detailed player statistics for each quarter.

* **5.1. CSV Data Input Format:**
  The CSV file will be structured to capture game details and then list player stats. A potential structure could involve a few header rows for game information, followed by player data rows.
  Alternatively, and more simply for parsing, each row could represent a player's stats for a specific game, with game information repeated or referenced. For simplicity of initial implementation, we'll assume a format where game information is provided once, followed by player rows.
  A more robust approach for multiple games in one file, or for clearer separation, would be to have distinct CSVs or sections, but for now, we'll focus on a single game import per CSV.

  **Example CSV Structure (`game_stats_template.csv`):**

  ```csv
  Home,Team A
  Visitor,Team B  
  Date,2025-05-15
  Team,Jersey Number,Player Name,Fouls,QT1,QT2,QT3,QT4
  Team A,10,Player One,2,22-1x,3/2,11,
  Team A,23,Player Two,3,12,x,-/,22
  Team B,5,Player Alpha,1,x,11,,33-
  Team B,15,Player Beta,4,2//1,2,x,1
  ```

  *   **Game Information (First 3 rows):**
      *   Row 1: `Home,<team_name>` - Name of the home team.
      *   Row 2: `Visitor,<team_name>` or `Away,<team_name>` - Name of the visiting/away team.
      *   Row 3: `Date,<date>` - Date of the game (supports YYYY-MM-DD or M/D/YYYY format).
  *   **Header Row (Row 4):**
      *   Contains column headers for player data. Headers are case-insensitive.
      *   `Team`: The team the player belongs to.
      *   `Jersey Number`, `Number`, or `Jersey`: Jersey number of the player.
      *   `Player Name`, `Player`, or `Name`: Full name of the player.
      *   `Fouls`: Total fouls committed by the player in the game (optional, defaults to 0).
      *   `QT1`, `QT2`, `QT3`, `QT4`: Shot strings for each quarter.
  *   **Player Data Rows (Row 5+):**
      *   Each row contains data for one player.
          *   An empty string for a quarter (e.g., `,,` in the CSV for QT3 of Player Alpha) indicates no shots or activity recorded for that quarter.
          *   **Shot String Character Legend (Configurable):** The characters used in the shot strings are defined in the application's configuration (e.g., in `app/config.py`). The following are default examples:
              *   `-`: Missed 2-point shot
              *   `/`: Missed 3-point shot
              *   `x`: Missed Free Throw (1-point)
              *   `1`: Made Free Throw (1-point)
              *   `2`: Made 2-point shot
              *   `3`: Made 3-point shot
          *   The configuration would map each character to its properties (e.g., shot type: FT, 2P, 3P; outcome: made/missed; point value).
          *   Example (using default mapping): `22-1x` means two made 2-point shots, one missed 2-point shot, one made free throw, one missed free throw.

* **5.2. CSV Import Process (handled by a CLI command, e.g., `basketball-stats import-game`):**
  *   The CLI command will accept a CSV file path as an argument (e.g., `basketball-stats import-game --file path/to/your/game_data.csv` or `-f path/to/your/game_data.csv`).
  *   The command (defined in `app/cli.py`) will read the CSV file, parsing the game information and then each player data row.
  *   **Validation:** Pydantic v2 models (e.g., defined in `app/web_ui/schemas.py` or a new `app/schemas/csv_schemas.py`) will be used to validate:
      *   The overall structure of the CSV (presence of required game info keys, player data headers).
      *   Each piece of game information (e.g., valid date format, team names not empty).
      *   Each player data row (e.g., jersey number is an integer, fouls is an integer, shot strings conform to expected patterns if strict validation is applied, or are just passed to the parser).
  *   If validation fails, the script will output clear error messages indicating the problematic row(s) and field(s).
  *   If validation succeeds:
      *   The script will call `game_service.py` to find or create game, home team, and away team records.
      *   For each player data row, it will call `player_service.py` to find or create player records.
      *   It will then call `stats_entry_service.py` to process the fouls and parse the shot strings (using `input_parser.py`) for each quarter, and then store these stats (PlayerGameStats, PlayerQuarterStats).
  *   The script will provide feedback to the user on successful import or any errors encountered.

* **5.3. Shot String Parsing (in `app/utils/input_parser.py`):**
  *   `parse_quarter_shot_string(shot_string: str) -> dict`: This function will take a shot string (e.g., "22-1x/") and return a dictionary with counts of makes and attempts for each shot type (FT, 2P, 3P). **It will use the configurable shot character mapping defined in `app/config.py` to interpret the characters.**
      *   Example input: `"22-1x/"` (assuming default character mapping)
      *   Example output: `{'ftm': 1, 'fta': 2, 'fg2m': 2, 'fg2a': 3, 'fg3m': 0, 'fg3a': 1}`
      *   It must correctly handle empty strings (no shots) by returning all counts as 0.
* **5.4. Storing Data (in `app/services/stats_entry_service.py` using CRUD functions from `app/data_access/crud/`):**
  *   The `stats_entry_service` will receive validated game ID, player ID, total fouls, and the per-quarter parsed shot data (makes/attempts for FT, 2P, 3P).
  *   It will use CRUD functions to:
      *   Create or update a `PlayerGameStats` record for the player in that game, including total fouls.
      *   For each quarter with shot data, create a `PlayerQuarterStats` record linked to the `PlayerGameStats` record, storing the ftm/a, fg2m/a, fg3m/a for that quarter.
      *   Aggregate the quarter stats to update the total makes/attempts in the `PlayerGameStats` record.

6. Output Display (Reporting - `app/reports/report_generator.py`)
The reporting system uses a direct CLI command, `basketball-stats report`, which provides options for console or CSV output formats (`--format`/`-f` parameter) and custom output filenames (`--output`/`-o` parameter). The implementation uses the `ReportGenerator` class to produce formatted box scores and game summaries.
7. Data Management: Output, Caching, Backups, Integrity
(Unchanged)
8. Future Considerations (Beyond Initial KISS Scope)
  * **Web UI for Data Entry and Reporting:** While the initial version focuses on CSV import for efficiency and simplicity, a future iteration could introduce a web-based user interface (potentially using Flask, as originally considered) for:
    *   Interactive data entry of game and player statistics, providing an alternative to CSV files.
    *   Viewing formatted game reports and box scores directly in a browser.
    *   Managing teams and players.
  * **Advanced Statistical Analysis:** Incorporate more complex calculations and reports (e.g., player efficiency ratings, team performance trends).
  * **User Authentication and Roles:** If multiple users need to manage data, implement user accounts and permission levels.
  * **API for Data Access:** Develop a RESTful API to allow other applications or services to consume the stats data.
  * **Real-time Updates:** For a more dynamic experience, explore options for real-time score updates during a game (though this significantly increases complexity).
  * **Database Migrations with Alembic:** Fully integrate Alembic for managing database schema changes as the application evolves.
  * **Enhanced CLI with Typer/Click:** Make the `basketball-stats` CLI (defined in `app/cli.py`) more robust and user-friendly.

**Dependencies to include in pyproject.toml:**

* Flask (for any potential future web UI for report viewing)
* SQLAlchemy (for ORM)
* Pydantic (version 2.x, for data validation)
* python-dotenv (for managing configuration, optional but good practice)
* tabulate (for CLI reports)
* Alembic (optional, for database migrations if schema evolves significantly)
* Typer or Click (optional, for a more structured CLI experience via `app/cli.py` and the `basketball-stats` entry point)
