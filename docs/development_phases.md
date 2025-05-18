# **Development Phases: Python Basketball Stats Tracker**

This document outlines a phased approach to developing the Python Basketball Stats Tracker application. Each phase includes a list of tasks with checkboxes. The emphasis is on defining structures (classes, functions, method signatures, inputs, outputs) before implementing the core logic, which is beneficial for clarity and AI-assisted development.

**Guiding Principles:**

* **KISS (Keep It Simple, Stupid):** Start with the most straightforward implementation for each feature.
* **SOLID:** Apply these principles as you design and implement classes and modules.
* **Iterative Development:** Build and test components incrementally.

**Phase 0: Project Setup & Configuration**

* [x] Initialize project directory structure as outlined in the Design Document (reflecting new app/data_access/crud/ and potentially app/schemas/csv_schemas.py).
* [x] Initialize Git repository.
* [x] Create pyproject.toml with basic project metadata (name, version, authors).
* [x] Add initial dependencies to pyproject.toml:
  * [x] flask (for potential future report UI)
  * [x] sqlalchemy
  * [x] pydantic>=2.0
  * [x] python-dotenv (optional, for config)
  * [x] alembic
  * [x] pytest (for testing)
  * [x] tabulate (for CLI reports)
  * [x] typer or click (for CLI in app/cli.py)
* [x] Create virtual environment and install dependencies.
* [x] Create app/config.py:
  * [x] Define class/structure for application settings (e.g., DATABASE_URL).
  * [x] **Define structure for configurable shot string character mapping.**
  * [x] Implement loading settings from environment variables (e.g., using python-dotenv and a .env file).
* [x] Create basic README.md with project description and setup instructions.
* [x] Create .gitignore file.

**Phase 1: Database Modeling & Setup (SQLAlchemy)**

* **1.1. Define SQLAlchemy Models (app/data_access/models.py):**
  * [x] Define Base declarative base for SQLAlchemy models.
  * [x] Define Team model class (attributes, relationships, __repr__).
  * [x] Define Player model class (attributes, relationships, unique constraints, __repr__).
  * [x] Define Game model class (attributes, relationships, __repr__).
  * [x] Define PlayerGameStats model class (attributes, relationships, unique constraint, __repr__).
  * [x] Define PlayerQuarterStats model class (attributes, relationships, unique & check constraints, __repr__).
* **1.2. Database Manager Setup (app/data_access/database_manager.py):**
  * [x] Define function get_engine(Inputs: db_url, Outputs: SQLAlchemy Engine).
  * [x] Define SessionLocal factory (Inputs: engine, Outputs: SQLAlchemy sessionmaker).
  * [x] Define function create_tables(engine: Engine) (Logic: Base.metadata.create_all(bind=engine)).
  * [x] Define context manager or dependency injector function get_db_session() for CLI commands/services to get a session.
* **1.3. Initial Database Creation:**
  * [x] Write a CLI command in app/cli.py (e.g., `basketball-stats init-db`) to initialize the database schema through Alembic migrations.
* **1.4. Alembic Setup:**
  * [x] Initialize and configure Alembic.
  * [x] Add capability to generate migrations based on model changes.

**Phase 2: Core Utilities (app/utils/)**

* **2.1. Input Parser (app/utils/input_parser.py):**
  * [x] Define function parse_quarter_shot_string(shot_string: str, shot_mapping: dict) -> dict (Inputs: shot_string, configured shot_mapping; Outputs: dict with ftm, fta, fg2m, fg2a, fg3m, fg3a; Docblock).
* **2.2. Stats Calculator (app/utils/stats_calculator.py):**
  * [x] Define calculate_percentage(makes: int, attempts: int) -> float | None.
  * [x] Define calculate_points(ftm: int, fg2m: int, fg3m: int) -> int.
  * [x] Define calculate_efg(total_fgm: int, fg3m: int, total_fga: int) -> float | None.
  * [x] Define calculate_ts(points: int, total_fga: int, fta: int) -> float | None.
* Logic for all utility functions: [Completed]

**Phase 3: Data Access Layer (DAL - app/data_access/crud/)**

* (Create individual files like app/data_access/crud/crud_team.py, app/data_access/crud/crud_player.py, etc.)
* (Each function will take db: Session as its first argument).
* **3.1. Team CRUD (app/data_access/crud/crud_team.py):**
  * [x] Define create_team(db: Session, team_name: str) -> models.Team.
  * [x] Define get_team_by_name(db: Session, team_name: str) -> models.Team | None.  # Used by roster & game stats import
  * [x] Define get_team_by_id(db: Session, team_id: int) -> models.Team | None.
  * [x] Define get_all_teams(db: Session) -> list[models.Team].
* **3.2. Player CRUD (app/data_access/crud/crud_player.py):**
  * [x] Define create_player(db: Session, name: str, jersey_number: int, team_id: int) -> models.Player. # Used by roster & game stats import
  * [x] Define get_player_by_team_and_jersey(db: Session, team_id: int, jersey_number: int) -> models.Player | None. # Used by roster & game stats import for conflict checking
  * [x] Define get_player_by_id(db: Session, player_id: int) -> models.Player | None. # Potentially used by game stats import
  * [x] Define get_players_by_team(db: Session, team_id: int) -> list[models.Player].
* **3.3. Game CRUD (app/data_access/crud/crud_game.py):**
  * [x] Define create_game(db: Session, date: str, playing_team_id: int, opponent_team_id: int) -> models.Game. # Used by game stats import
  * [x] Define get_game_by_id(db: Session, game_id: int) -> models.Game | None.
  * [x] Define get_games_by_team(db: Session, team_id: int) -> list[models.Game].
  * [x] Define get_games_by_date_range(db: Session, start_date: str, end_date: str) -> list[models.Game].
* **3.4. PlayerGameStats CRUD (app/data_access/crud/crud_player_game_stats.py):**
  * [x] Define create_player_game_stats(db: Session, game_id: int, player_id: int, fouls: int) -> models.PlayerGameStats. # Used by game stats import
  * [x] Define update_player_game_stats_totals(db: Session, player_game_stat_id: int, totals: dict) -> models.PlayerGameStats. # Used by game stats import
  * [x] Define get_player_game_stats_by_game(db: Session, game_id: int) -> list[models.PlayerGameStats].
  * [x] Define get_player_game_stats(db: Session, player_game_stat_id: int) -> models.PlayerGameStats | None.
* **3.5. PlayerQuarterStats CRUD (app/data_access/crud/crud_player_quarter_stats.py):**
  * [x] Define create_player_quarter_stats(db: Session, player_game_stat_id: int, quarter_number: int, stats: dict) -> models.PlayerQuarterStats. # Used by game stats import
  * [x] Define get_player_quarter_stats(db: Session, player_game_stat_id: int) -> list[models.PlayerQuarterStats].
  * [x] Define get_quarter_stats_by_quarter(db: Session, player_game_stat_id: int, quarter_number: int) -> models.PlayerQuarterStats | None.
* Logic for all CRUD functions: [Completed]

**Phase 4: Service Layer (app/services/) & CSV Schemas**

* **4.0. Pydantic Schemas for CSV Data (app/web_ui/schemas.py or app/schemas/csv_schemas.py):**
  * [x] Define GameInfoSchema(BaseModel): playing_team, opponent_team, date.
  * [x] Define PlayerStatsRowSchema(BaseModel): team_name, player_jersey, player_name, fouls, qt1_shots, qt2_shots, qt3_shots, qt4_shots.
  * [x] Define GameStatsCSVInputSchema(BaseModel): game_info: GameInfoSchema, player_stats: list[PlayerStatsRowSchema].
* (Pydantic models for service layer inputs/outputs (DTOs) can be defined in app/services/schemas.py if they differ from CSV schemas, or reuse/extend for KISS).
* **4.1. Game Service (app/services/game_service.py):**
  * [x] Define class GameService:
    * [x] __init__(self, db_session: Session).
    * [x] add_game(self, date: str, playing_team_name: str, opponent_team_name: str) -> GameDataSchema (or models.Game).
    * [x] get_or_create_team(self, team_name: str) -> TeamDataSchema (or models.Team).
    * [x] list_all_teams(self) -> list[TeamDataSchema] (or list[models.Team]).
* **4.2. Player Service (app/services/player_service.py):**
  * [x] Define class PlayerService:
    * [x] __init__(self, db_session: Session).
    * [x] get_or_create_player(self, team_id: int, jersey_number: int, player_name: str | None = None) -> PlayerDataSchema (or models.Player).
    * [x] get_player_details(self, player_id: int) -> models.Player | None.
    * [x] get_team_roster(self, team_id: int) -> list[models.Player].
* **4.3. Stats Entry Service (app/services/stats_entry_service.py):**
  * [x] Define class StatsEntryService:
    * [x] __init__(self, db_session: Session, input_parser_func, shot_mapping: dict).
    * [x] record_player_game_performance(self, game_id: int, player_id: int, fouls: int, quarter_shot_strings: list[str]) -> PlayerGameStatsDataSchema (or models.PlayerGameStats).
* Logic for all service methods: [Completed]

**Phase 5: CSV Import CLI (app/cli.py)**

* **5.1. Roster Import Command (`basketball-stats import-roster`):**
  * [x] Define Typer command for roster import.
  * [x] Logic to read CSV, validate with Pydantic, use PlayerService/TeamService (or direct CRUD) to add players/teams.
  * [x] --dry-run option.
* **5.2. Game Stats Import Command (`basketball-stats import-game-stats`):**
  * [x] Define Typer command for game stats import.
  * [x] Argument for CSV file path.
  * [x] Logic:
    *   [x] Get DB session.
    *   [x] Load shot string mapping from `app/config.py`.
    *   [x] Read and parse CSV file (header for game info, subsequent rows for player stats).
    *   [x] Validate parsed data using Pydantic schemas (from Phase 4.0).
    *   [x] Instantiate GameService, PlayerService, StatsEntryService (passing shot_mapping to StatsEntryService).
    *   [x] Use GameService to add/get game and teams.
    *   [x] Loop through validated player data:
        *   [x] Use PlayerService to get/create player.
        *   [x] Use StatsEntryService to record player game performance (fouls, parsed quarter stats).
    *   [x] Provide user feedback (success/errors).
* Logic for CLI commands: [Completed]

**Phase 6: Reporting (app/reports/ and app/cli.py)**

* **6.1. Report Generator (app/reports/report_generator.py):**
  * [x] Define class ReportGenerator:
    * [x] __init__(self, db_session: Session, stats_calculator_module).
    * [x] get_game_box_score_data(self, game_id: int) -> tuple[list[dict], dict].
* **6.2. CLI for Report Generation (app/cli.py):**
  * [x] Use typer for command-line arguments (e.g., `basketball-stats report --game-id 1 --format csv`).
  * [x] Implement main CLI function:
    * [x] Sets up DB session.
    * [x] Instantiates ReportGenerator.
    * [x] Calls get_game_box_score_data().
    * [x] Outputs to console using tabulate or to CSV file using csv module.
* Logic for report generation: [Completed]

**Phase 7: Testing & Refinement**

* **7.1. Unit Tests (tests/):**
  * [ ] test_input_parser.py (with various shot strings and mappings).
  * [ ] test_stats_calculator.py.
  * [ ] Tests for service layer methods (mocking DAL, focusing on logic for CSV processing).
  * [ ] Tests for DAL CRUD functions (can use an in-memory SQLite).
  * [ ] Tests for Pydantic schema validation (CSV and internal).
* **7.2. Integration Tests:**
  * [ ] Test the full CSV import flow for game stats.
  * [ ] Test CLI roster import.
  * [ ] Test CLI report generation.
* **7.3. Refinement:**
  * [ ] Code review.
  * [ ] Improve error handling and user feedback.
  * [ ] Logging.
  * [ ] Docstrings.

**Phase 8: Future Considerations (Web UI for Reporting)**

* This phase is deferred. If a Web UI is developed, it would likely focus on displaying reports rather than data entry.
* **8.1. Pydantic Schemas for Web Display (app/web_ui/schemas.py - if different from service DTOs):**
  * [ ] Define schemas suitable for presenting data in HTML templates.
* **8.2. Flask App Initialization (app/main.py):**
  * [ ] Define function create_app():
    * Initializes Flask app instance (Flask(__name__, template_folder='web_ui/templates')).
    * Loads configuration from app/config.py.
    * Sets up database session handling for requests.
    * Imports and registers Blueprints from app/web_ui/routes.py.
    * Returns the app instance.
* **8.3. HTML Templates (app/web_ui/templates/):**
  * [ ] Create HTML templates for displaying game summaries, leaderboards, etc.
* **8.4. Flask Routes (app/web_ui/routes.py):**
  * [ ] Create a Flask Blueprint.
  * [ ] Define routes for displaying reports (e.g., /games, /games/<game_id>/summary).
    * Logic: Fetch data using services, render templates.

This refined plan further separates concerns, making each module's responsibility clearer and aligning better with SOLID principles, which should aid AI-assisted development by providing more focused tasks.