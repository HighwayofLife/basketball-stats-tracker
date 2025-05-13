# **Development Phases: Python Basketball Stats Tracker**

This document outlines a phased approach to developing the Python Basketball Stats Tracker application. Each phase includes a list of tasks with checkboxes. The emphasis is on defining structures (classes, functions, method signatures, inputs, outputs) before implementing the core logic, which is beneficial for clarity and AI-assisted development.

**Guiding Principles:**

* **KISS (Keep It Simple, Stupid):** Start with the most straightforward implementation for each feature.  
* **SOLID:** Apply these principles as you design and implement classes and modules.  
* **Iterative Development:** Build and test components incrementally.

**Phase 0: Project Setup & Configuration**

* [x] Initialize project directory structure as outlined in the Design Document (reflecting new app/data_access/crud/ and app/web_ui/routes.py).  
* [x] Initialize Git repository.  
* [x] Create pyproject.toml with basic project metadata (name, version, authors).  
* [x] Add initial dependencies to pyproject.toml:  
  * [x] flask  
  * [x] sqlalchemy  
  * [x] pydantic>=2.0  
  * [x] python-dotenv (optional, for config)  
  * [x] alembic (optional, for migrations - can defer)  
  * [x] pytest (for testing)  
  * [x] tabulate (for CLI reports)  
  * [x] typer or click (optional, for a more robust CLI in run_cli.py)  
* [ ] Create virtual environment and install dependencies.  
* [x] Create app/config.py:  
  * [ ] Define class/structure for application settings (e.g., DATABASE_URL, SECRET_KEY for Flask).  
  * [ ] Implement loading settings from environment variables (e.g., using python-dotenv and a .env file).  
* [x] Create basic README.md with project description and setup instructions.  
* [x] Create .gitignore file.

**Phase 1: Database Modeling & Setup (SQLAlchemy)**

* **1.1. Define SQLAlchemy Models (app/data_access/models.py):**  
  * [ ] Define Base declarative base for SQLAlchemy models.  
  * [ ] Define Team model class (attributes, relationships, __repr__).  
  * [ ] Define Player model class (attributes, relationships, unique constraints, __repr__).  
  * [ ] Define Game model class (attributes, relationships, __repr__).  
  * [ ] Define PlayerGameStats model class (attributes, relationships, unique constraint, __repr__).  
  * [ ] Define PlayerQuarterStats model class (attributes, relationships, unique & check constraints, __repr__).  
* **1.2. Database Manager Setup (app/data_access/database_manager.py):**  
  * [ ] Define function get_engine(Inputs: db_url, Outputs: SQLAlchemy Engine).  
  * [ ] Define SessionLocal factory (Inputs: engine, Outputs: SQLAlchemy sessionmaker).  
  * [ ] Define function create_tables(engine: Engine) (Logic: Base.metadata.create_all(bind=engine)).  
  * [ ] Define context manager or dependency injector function get_db_session() for Flask routes/services to get a session.  
* **1.3. Initial Database Creation:**  
  * [ ] Write a simple script (e.g., a command in run_cli.py or a temporary section in app/main.py) to call create_tables().  
* **1.4. (Optional) Alembic Setup:**  
  * [ ] Initialize and configure Alembic.  
  * [ ] Generate initial migration based on models.

**Phase 2: Core Utilities (app/utils/)**

* **2.1. Input Parser (app/utils/input_parser.py):**  
  * [ ] Define function parse_quarter_shot_string(shot_string: str) -> dict (Inputs, Outputs, Docblock as before).  
* **2.2. Stats Calculator (app/utils/stats_calculator.py):**  
  * [ ] Define calculate_percentage(makes: int, attempts: int) -> float | None.  
  * [ ] Define calculate_points(ftm: int, fg2m: int, fg3m: int) -> int.  
  * [ ] Define calculate_efg(total_fgm: int, fg3m: int, total_fga: int) -> float | None.  
  * [ ] Define calculate_ts(points: int, total_fga: int, fta: int) -> float | None.  
* Logic for all utility functions: (Implement after structure is defined).

**Phase 3: Data Access Layer (DAL - app/data_access/crud/)**

* (Create individual files like app/data_access/crud/crud_team.py, app/data_access/crud/crud_player.py, etc.)  
* (Each function will take db: Session as its first argument).  
* **3.1. Team CRUD (app/data_access/crud/crud_team.py):**  
  * [ ] Define create_team(db: Session, team_name: str) -> models.Team.  
  * [ ] Define get_team_by_name(db: Session, team_name: str) -> models.Team | None.  
  * [ ] Define get_team_by_id(db: Session, team_id: int) -> models.Team | None.  
  * [ ] Define get_all_teams(db: Session) -> list[models.Team].  
* **3.2. Player CRUD (app/data_access/crud/crud_player.py):**  
  * [ ] Define create_player(db: Session, name: str, jersey_number: int, team_id: int) -> models.Player.  
  * [ ] Define get_player_by_team_and_jersey(db: Session, team_id: int, jersey_number: int) -> models.Player | None.  
  * [ ] Define get_player_by_id(db: Session, player_id: int) -> models.Player | None.  
* **3.3. Game CRUD (app/data_access/crud/crud_game.py):**  
  * [ ] Define create_game(db: Session, date: str, playing_team_id: int, opponent_team_id: int) -> models.Game.  
  * [ ] Define get_game_by_id(db: Session, game_id: int) -> models.Game | None.  
* **3.4. PlayerGameStats CRUD (app/data_access/crud/crud_player_game_stats.py):**  
  * [ ] Define create_player_game_stats(db: Session, game_id: int, player_id: int, fouls: int) -> models.PlayerGameStats.  
  * [ ] Define update_player_game_stats_totals(db: Session, player_game_stat_id: int, totals: dict) -> models.PlayerGameStats.  
  * [ ] Define get_player_game_stats_by_game(db: Session, game_id: int) -> list[models.PlayerGameStats].  
* **3.5. PlayerQuarterStats CRUD (app/data_access/crud/crud_player_quarter_stats.py):**  
  * [ ] Define create_player_quarter_stats(db: Session, player_game_stat_id: int, quarter_number: int, stats: dict) -> models.PlayerQuarterStats.  
  * [ ] Define get_player_quarter_stats(db: Session, player_game_stat_id: int) -> list[models.PlayerQuarterStats].  
* Logic for all CRUD functions: (Implement after structure is defined).

**Phase 4: Service Layer (app/services/)**

* (Pydantic models for service layer inputs/outputs (DTOs) can be defined in app/services/schemas.py if they differ from web schemas, or reuse/extend app/web_ui/schemas.py for KISS).  
* **4.1. Game Service (app/services/game_service.py):**  
  * [ ] Define class GameService:  
    * [ ] __init__(self, db_session: Session).  
    * [ ] add_game(self, date: str, playing_team_name: str, opponent_team_name: str) -> GameDataSchema.  
    * [ ] get_or_create_team(self, team_name: str) -> TeamDataSchema.  
    * [ ] list_all_teams(self) -> list[TeamDataSchema].  
* **4.2. Player Service (app/services/player_service.py):**  
  * [ ] Define class PlayerService:  
    * [ ] __init__(self, db_session: Session).  
    * [ ] get_or_create_player(self, team_id: int, jersey_number: int, player_name: str | None = None) -> PlayerDataSchema.  
* **4.3. Stats Entry Service (app/services/stats_entry_service.py):**  
  * [ ] Define class StatsEntryService:  
    * [ ] __init__(self, db_session: Session, input_parser_func).  
    * [ ] record_player_game_performance(self, game_id: int, player_id: int, fouls: int, quarter_shot_strings: list[str]) -> PlayerGameStatsDataSchema.  
* Logic for all service methods: (Implement after structure is defined).

**Phase 5: Web UI (Flask)**

* **5.1. Pydantic Schemas for Form Data (app/web_ui/schemas.py):**  
  * [ ] Define PlayerWebInputSchema(BaseModel): jersey_number (str to allow empty), fouls (int), q1_shots (str), etc. *Consider how to handle empty player rows.*  
  * [ ] Define GameWebInputFormSchema(BaseModel): your_team_name (str), date (str), opponent_team_name (str), players: list[PlayerWebInputSchema | None](list of 10, some can be None or have empty jersey numbers).  
* **5.2. Flask App Initialization (app/main.py):**  
  * [ ] Define function create_app():  
    * Initializes Flask app instance (Flask(__name__, template_folder='web_ui/templates')).  
    * Loads configuration from app/config.py.  
    * Sets up database session handling for requests (e.g., using @app.before_request and @app.teardown_request or a Flask extension).  
    * Imports and registers Blueprints from app/web_ui/routes.py.  
    * Returns the app instance.  
* **5.3. HTML Form (app/web_ui/templates/form.html):**  
  * [ ] Create HTML structure (top-level fields, ~10 player rows).  
  * [ ] Ensure input field names allow for easy parsing by Flask and Pydantic (e.g., players-0-jersey_number).  
  * [ ] Add basic styling.  
  * [ ] Implement display of validation errors passed from the route.  
* **5.4. Flask Routes (app/web_ui/routes.py):**  
  * [ ] Create a Flask Blueprint (e.g., web_ui_bp = Blueprint('web_ui', __name__)).  
  * [ ] Define route / or /enter_stats (GET) attached to the Blueprint:  
    * Logic:  
      * Get DB session.  
      * Instantiate GameService.  
      * Fetch team names using game_service.list_all_teams() for dropdowns.  
      * Render form.html, passing team names and any form data/errors for re-population.  
  * [ ] Define route /submit_stats (POST) attached to the Blueprint:  
    * Logic:  
      * Get DB session.  
      * Parse request.form data. Carefully handle the list of player inputs.  
      * Instantiate GameWebInputFormSchema with parsed data.  
      * If validation fails, re-render form.html with errors and existing form data.  
      * If validation succeeds:  
        * Instantiate GameService, PlayerService, StatsEntryService.  
        * Call game_service.add_game().  
        * Loop through validated player data (ignoring empty player rows):  
          * Call player_service.get_or_create_player().  
          * Call stats_entry_service.record_player_game_performance().  
        * Set flash message for success.  
        * Redirect to the GET route for the form (or a dedicated success page).  
* Logic for routes: (Implement after structure is defined).

**Phase 6: Reporting (app/reports/ and run_cli.py)**

* **6.1. Report Generator (app/reports/report_generator.py):**  
  * [ ] Define class ReportGenerator:  
    * [ ] __init__(self, db_session: Session, stats_calculator_module).  
    * [ ] get_game_box_score_data(self, game_id: int) -> tuple[list[dict], dict].  
* **6.2. CLI for Report Generation (run_cli.py at project root):**  
  * [ ] Use typer or argparse for command-line arguments (e.g., report --game-id 1 --format csv).  
  * [ ] Implement main CLI function:  
    * Sets up DB session.  
    * Instantiates ReportGenerator.  
    * Calls get_game_box_score_data().  
    * Outputs to console using tabulate or to CSV file using csv module.  
* Logic for report generation: (Implement after structure is defined).

**Phase 7: Testing & Refinement**

* **7.1. Unit Tests (tests/):**  
  * [ ] test_input_parser.py.  
  * [ ] test_stats_calculator.py.  
  * [ ] Tests for service layer methods (mocking DAL).  
  * [ ] Tests for DAL CRUD functions (can use an in-memory SQLite).  
  * [ ] Tests for Pydantic schema validation.  
* **7.2. Integration Tests:**  
  * [ ] Test the full data entry web flow.  
  * [ ] Test CLI report generation.  
* **7.3. Refinement:**  
  * [ ] Code review.  
  * [ ] Improve error handling and user feedback.  
  * [ ] Logging.  
  * [ ] Docstrings.

This refined plan further separates concerns, making each module's responsibility clearer and aligning better with SOLID principles, which should aid AI-assisted development by providing more focused tasks.