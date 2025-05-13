# **Development Phases: Python Basketball Stats Tracker**

This document outlines a phased approach to developing the Python Basketball Stats Tracker application. Each phase includes a list of tasks with checkboxes. The emphasis is on defining structures (classes, functions, method signatures, inputs, outputs) before implementing the core logic, which is beneficial for clarity and AI-assisted development.

**Guiding Principles:**

* **KISS (Keep It Simple, Stupid):** Start with the most straightforward implementation for each feature.  
* **SOLID:** Apply these principles as you design and implement classes and modules.  
* **Iterative Development:** Build and test components incrementally.

**Phase 0: Project Setup & Configuration**

* [ ] Initialize project directory structure as outlined in the Design Document (reflecting new app/data\_access/crud/ and app/web\_ui/routes.py).  
* [ ] Initialize Git repository.  
* [ ] Create pyproject.toml with basic project metadata (name, version, authors).  
* [ ] Add initial dependencies to pyproject.toml:  
  * [ ] flask  
  * [ ] sqlalchemy  
  * [ ] pydantic\>=2.0  
  * [ ] python-dotenv (optional, for config)  
  * [ ] alembic (optional, for migrations \- can defer)  
  * [ ] pytest (for testing)  
  * [ ] tabulate (for CLI reports)  
  * [ ] typer or click (optional, for a more robust CLI in run\_cli.py)  
* [ ] Create virtual environment and install dependencies.  
* [ ] Create app/config.py:  
  * [ ] Define class/structure for application settings (e.g., DATABASE\_URL, SECRET\_KEY for Flask).  
  * [ ] Implement loading settings from environment variables (e.g., using python-dotenv and a .env file).  
* [ ] Create basic README.md with project description and setup instructions.  
* [ ] Create .gitignore file.

**Phase 1: Database Modeling & Setup (SQLAlchemy)**

* **1.1. Define SQLAlchemy Models (app/data\_access/models.py):**  
  * [ ] Define Base declarative base for SQLAlchemy models.  
  * [ ] Define Team model class (attributes, relationships, \_\_repr\_\_).  
  * [ ] Define Player model class (attributes, relationships, unique constraints, \_\_repr\_\_).  
  * [ ] Define Game model class (attributes, relationships, \_\_repr\_\_).  
  * [ ] Define PlayerGameStats model class (attributes, relationships, unique constraint, \_\_repr\_\_).  
  * [ ] Define PlayerQuarterStats model class (attributes, relationships, unique & check constraints, \_\_repr\_\_).  
* **1.2. Database Manager Setup (app/data\_access/database\_manager.py):**  
  * [ ] Define function get\_engine() (Inputs: db\_url, Outputs: SQLAlchemy Engine).  
  * [ ] Define SessionLocal factory (Inputs: engine, Outputs: SQLAlchemy sessionmaker).  
  * [ ] Define function create\_tables(engine: Engine) (Logic: Base.metadata.create\_all(bind=engine)).  
  * [ ] Define context manager or dependency injector function get\_db\_session() for Flask routes/services to get a session.  
* **1.3. Initial Database Creation:**  
  * [ ] Write a simple script (e.g., a command in run\_cli.py or a temporary section in app/main.py) to call create\_tables().  
* **1.4. (Optional) Alembic Setup:**  
  * [ ] Initialize and configure Alembic.  
  * [ ] Generate initial migration based on models.

**Phase 2: Core Utilities (app/utils/)**

* **2.1. Input Parser (app/utils/input\_parser.py):**  
  * [ ] Define function parse\_quarter\_shot\_string(shot\_string: str) \-\> dict (Inputs, Outputs, Docblock as before).  
* **2.2. Stats Calculator (app/utils/stats\_calculator.py):**  
  * [ ] Define calculate\_percentage(makes: int, attempts: int) \-\> float | None.  
  * [ ] Define calculate\_points(ftm: int, fg2m: int, fg3m: int) \-\> int.  
  * [ ] Define calculate\_efg(total\_fgm: int, fg3m: int, total\_fga: int) \-\> float | None.  
  * [ ] Define calculate\_ts(points: int, total\_fga: int, fta: int) \-\> float | None.  
* Logic for all utility functions: (Implement after structure is defined).

**Phase 3: Data Access Layer (DAL \- app/data\_access/crud/)**

* (Create individual files like app/data\_access/crud/crud\_team.py, app/data\_access/crud/crud\_player.py, etc.)  
* (Each function will take db: Session as its first argument).  
* **3.1. Team CRUD (app/data\_access/crud/crud\_team.py):**  
  * [ ] Define create\_team(db: Session, team\_name: str) \-\> models.Team.  
  * [ ] Define get\_team\_by\_name(db: Session, team\_name: str) \-\> models.Team | None.  
  * [ ] Define get\_team\_by\_id(db: Session, team\_id: int) \-\> models.Team | None.  
  * [ ] Define get\_all\_teams(db: Session) \-\> list\[models.Team\].  
* **3.2. Player CRUD (app/data\_access/crud/crud\_player.py):**  
  * [ ] Define create\_player(db: Session, name: str, jersey\_number: int, team\_id: int) \-\> models.Player.  
  * [ ] Define get\_player\_by\_team\_and\_jersey(db: Session, team\_id: int, jersey\_number: int) \-\> models.Player | None.  
  * [ ] Define get\_player\_by\_id(db: Session, player\_id: int) \-\> models.Player | None.  
* **3.3. Game CRUD (app/data\_access/crud/crud\_game.py):**  
  * [ ] Define create\_game(db: Session, date: str, playing\_team\_id: int, opponent\_team\_id: int) \-\> models.Game.  
  * [ ] Define get\_game\_by\_id(db: Session, game\_id: int) \-\> models.Game | None.  
* **3.4. PlayerGameStats CRUD (app/data\_access/crud/crud\_player\_game\_stats.py):**  
  * [ ] Define create\_player\_game\_stats(db: Session, game\_id: int, player\_id: int, fouls: int) \-\> models.PlayerGameStats.  
  * [ ] Define update\_player\_game\_stats\_totals(db: Session, player\_game\_stat\_id: int, totals: dict) \-\> models.PlayerGameStats.  
  * [ ] Define get\_player\_game\_stats\_by\_game(db: Session, game\_id: int) \-\> list\[models.PlayerGameStats\].  
* **3.5. PlayerQuarterStats CRUD (app/data\_access/crud/crud\_player\_quarter\_stats.py):**  
  * [ ] Define create\_player\_quarter\_stats(db: Session, player\_game\_stat\_id: int, quarter\_number: int, stats: dict) \-\> models.PlayerQuarterStats.  
  * [ ] Define get\_player\_quarter\_stats(db: Session, player\_game\_stat\_id: int) \-\> list\[models.PlayerQuarterStats\].  
* Logic for all CRUD functions: (Implement after structure is defined).

**Phase 4: Service Layer (app/services/)**

* (Pydantic models for service layer inputs/outputs (DTOs) can be defined in app/services/schemas.py if they differ from web schemas, or reuse/extend app/web\_ui/schemas.py for KISS).  
* **4.1. Game Service (app/services/game\_service.py):**  
  * [ ] Define class GameService:  
    * [ ] \_\_init\_\_(self, db\_session: Session).  
    * [ ] add\_game(self, date: str, playing\_team\_name: str, opponent\_team\_name: str) \-\> GameDataSchema.  
    * [ ] get\_or\_create\_team(self, team\_name: str) \-\> TeamDataSchema.  
    * [ ] list\_all\_teams(self) \-\> list\[TeamDataSchema\].  
* **4.2. Player Service (app/services/player\_service.py):**  
  * [ ] Define class PlayerService:  
    * [ ] \_\_init\_\_(self, db\_session: Session).  
    * [ ] get\_or\_create\_player(self, team\_id: int, jersey\_number: int, player\_name: str | None \= None) \-\> PlayerDataSchema.  
* **4.3. Stats Entry Service (app/services/stats\_entry\_service.py):**  
  * [ ] Define class StatsEntryService:  
    * [ ] \_\_init\_\_(self, db\_session: Session, input\_parser\_func).  
    * [ ] record\_player\_game\_performance(self, game\_id: int, player\_id: int, fouls: int, quarter\_shot\_strings: list\[str\]) \-\> PlayerGameStatsDataSchema.  
* Logic for all service methods: (Implement after structure is defined).

**Phase 5: Web UI (Flask)**

* **5.1. Pydantic Schemas for Form Data (app/web\_ui/schemas.py):**  
  * [ ] Define PlayerWebInputSchema(BaseModel): jersey\_number (str to allow empty), fouls (int), q1\_shots (str), etc. *Consider how to handle empty player rows.*  
  * [ ] Define GameWebInputFormSchema(BaseModel): your\_team\_name (str), date (str), opponent\_team\_name (str), players: list\[PlayerWebInputSchema | None\] (list of 10, some can be None or have empty jersey numbers).  
* **5.2. Flask App Initialization (app/main.py):**  
  * [ ] Define function create\_app():  
    * Initializes Flask app instance (Flask(\_\_name\_\_, template\_folder='web\_ui/templates')).  
    * Loads configuration from app/config.py.  
    * Sets up database session handling for requests (e.g., using @app.before\_request and @app.teardown\_request or a Flask extension).  
    * Imports and registers Blueprints from app/web\_ui/routes.py.  
    * Returns the app instance.  
* **5.3. HTML Form (app/web\_ui/templates/form.html):**  
  * [ ] Create HTML structure (top-level fields, \~10 player rows).  
  * [ ] Ensure input field names allow for easy parsing by Flask and Pydantic (e.g., players-0-jersey\_number).  
  * [ ] Add basic styling.  
  * [ ] Implement display of validation errors passed from the route.  
* **5.4. Flask Routes (app/web\_ui/routes.py):**  
  * [ ] Create a Flask Blueprint (e.g., web\_ui\_bp \= Blueprint('web\_ui', \_\_name\_\_)).  
  * [ ] Define route / or /enter\_stats (GET) attached to the Blueprint:  
    * Logic:  
      * Get DB session.  
      * Instantiate GameService.  
      * Fetch team names using game\_service.list\_all\_teams() for dropdowns.  
      * Render form.html, passing team names and any form data/errors for re-population.  
  * [ ] Define route /submit\_stats (POST) attached to the Blueprint:  
    * Logic:  
      * Get DB session.  
      * Parse request.form data. Carefully handle the list of player inputs.  
      * Instantiate GameWebInputFormSchema with parsed data.  
      * If validation fails, re-render form.html with errors and existing form data.  
      * If validation succeeds:  
        * Instantiate GameService, PlayerService, StatsEntryService.  
        * Call game\_service.add\_game().  
        * Loop through validated player data (ignoring empty player rows):  
          * Call player\_service.get\_or\_create\_player().  
          * Call stats\_entry\_service.record\_player\_game\_performance().  
        * Set flash message for success.  
        * Redirect to the GET route for the form (or a dedicated success page).  
* Logic for routes: (Implement after structure is defined).

**Phase 6: Reporting (app/reports/ and run\_cli.py)**

* **6.1. Report Generator (app/reports/report\_generator.py):**  
  * [ ] Define class ReportGenerator:  
    * [ ] \_\_init\_\_(self, db\_session: Session, stats\_calculator\_module).  
    * [ ] get\_game\_box\_score\_data(self, game\_id: int) \-\> tuple\[list\[dict\], dict\].  
* **6.2. CLI for Report Generation (run\_cli.py at project root):**  
  * [ ] Use typer or argparse for command-line arguments (e.g., report \--game-id 1 \--format csv).  
  * [ ] Implement main CLI function:  
    * Sets up DB session.  
    * Instantiates ReportGenerator.  
    * Calls get\_game\_box\_score\_data().  
    * Outputs to console using tabulate or to CSV file using csv module.  
* Logic for report generation: (Implement after structure is defined).

**Phase 7: Testing & Refinement**

* **7.1. Unit Tests (tests/):**  
  * [ ] test\_input\_parser.py.  
  * [ ] test\_stats\_calculator.py.  
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