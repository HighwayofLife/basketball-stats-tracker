# **Technical Design Document: Python Basketball Stats Tracker**

**1\. Introduction**

* 1.1. Purpose:  
  To develop a simple Python application with a basic web UI for tracking basketball game statistics for a small league. The application will allow users to input game details, individual player performance per quarter (fouls and a simplified shot string) via a web form, store this data persistently using SQLAlchemy, validate data with Pydantic v2, and generate game summary reports.  
* **1.2. Goals:**  
  * **Simplicity (KISS):** Focus on core functionality, straightforward data structures, and a simple web UI (Flask) for data entry. Avoid over-engineering.  
  * **Maintainability (SOLID):** Structure the application with clear separation of concerns.  
  * **Efficient Data Entry:** Allow for quick input of game stats via a structured web form.  
  * **Accurate Storage:** Persistently store raw makes and attempts for Free Throws (FT), 2-Point Field Goals (2P), and 3-Point Field Goals (3P) by quarter for each player.  
  * **Basic Reporting:** Output game statistics in a clear tabular format or as a CSV file.  
* **1.3. Scope:**  
  * **Input:** Game information (teams, date), player fouls, and per-quarter shot strings for each player, entered via a web form. Data validation using Pydantic v2.  
  * **Storage:** SQLite database with SQLAlchemy as the ORM.  
  * **Processing:** Parsing shot strings into makes/attempts per quarter, aggregating for game totals.  
  * **Output:** Game box score table.  
  * **Initial Version:** Focus on data entry via a simple web UI.

**2\. System Architecture**

The application will follow a layered architecture:

* **2.1. Presentation Layer (Simple Web UI \- Flask):**  
  * A basic HTML form served by Flask.  
  * Form submission will be handled by Flask routes defined in a dedicated routes module.  
  * This layer is responsible for rendering the input form and sending the collected data (validated using Pydantic models) to the service layer.  
  * Files: app/main.py (Flask app initialization), app/web\_ui/routes.py (Flask route definitions), app/web\_ui/templates/form.html. Pydantic models for form data validation reside in app/web\_ui/schemas.py.  
* **2.2. Service Layer (Business Logic \- app/services/):**  
  * Contains the core application logic.  
  * Coordinates interactions between the Web UI's backend handler and the Data Access Layer.  
* **2.3. Data Access Layer (DAL \- app/data\_access/):**  
  * Encapsulates all database interactions using SQLAlchemy.  
  * Defines SQLAlchemy models for database tables.  
  * Provides an API for the service layer to interact with the database, with CRUD operations organized per model.  
  * Files: app/data\_access/database\_manager.py (handles SQLAlchemy engine and session setup), app/data\_access/models.py (SQLAlchemy model definitions), and app/data\_access/crud/ (directory containing CRUD operations specific to each model, e.g., crud\_team.py).  
* **2.4. Utility Layer (app/utils/):**  
  * input\_parser.py: Parses quarter shot strings.  
  * stats\_calculator.py: Calculates derived statistics.  
* **2.5. Database:**  
  * SQLite (data/league\_stats.db) accessed via SQLAlchemy.

**3\. File Layout**

```
basketball\_stats\_tracker/  
├── app/  
│   ├── main.py                 \# Flask app initialization, registers Blueprints  
│   ├── config.py               \# Application configuration  
│   │  
│   ├── web\_ui/  
│   │   ├── routes.py           \# Flask Blueprint with route definitions  
│   │   ├── templates/  
│   │   │   └── form.html       \# HTML template for the data entry form  
│   │   └── schemas.py          \# Pydantic models for web form data validation  
│   │  
│   ├── services/  
│   │   ├── game\_service.py  
│   │   ├── player\_service.py  
│   │   └── stats\_entry\_service.py  
│   │  
│   ├── data\_access/  
│   │   ├── database\_manager.py \# SQLAlchemy setup, session management  
│   │   ├── models.py           \# SQLAlchemy ORM models  
│   │   └── crud/               \# Directory for CRUD operations per model  
│   │       ├── crud\_team.py  
│   │       ├── crud\_player.py  
│   │       └── ...             \# etc.  
│   │  
│   ├── utils/  
│   │   ├── input\_parser.py  
│   │   └── stats\_calculator.py  
│   │  
│   └── reports/  
│       └── report\_generator.py \# Generates output tables/CSVs  
│  
├── data/                       \# Directory to store the SQLite database file  
│   └── league\_stats.db  
│  
├── tests/                      \# Directory for unit/integration tests  
│   ├── test\_input\_parser.py  
│   └── test\_stats\_calculator.py  
│  
├── run\_cli.py                  \# Script for CLI tasks (e.g., DB setup, report generation)  
├── pyproject.toml              \# Project metadata and dependencies  
└── README.md                   \# Project overview and setup instructions
```

**4\. Data Model (Database Schema \- SQLAlchemy ORM Models)**

*(This section remains unchanged from the previous version where SQLAlchemy models were introduced: Team, Player, Game, PlayerGameStats, PlayerQuarterStats models as defined in app/data\_access/models.py.)*

* **4.1. Team Model (corresponds to Teams Table)**  
  * id (Integer, primary\_key=True, autoincrement=True)  
  * name (String, unique=True, nullable=False)  
  * players (relationship backref to Player)  
  * home\_games (relationship backref to Game where team is playing\_team)  
  * away\_games (relationship backref to Game where team is opponent\_team)  
* **4.2. Player Model (corresponds to Players Table)**  
  * id (Integer, primary\_key=True, autoincrement=True)  
  * team\_id (Integer, ForeignKey('teams.id'), nullable=False)  
  * name (String, nullable=False)  
  * jersey\_number (Integer, nullable=False)  
  * team (relationship to Team)  
  * game\_stats (relationship backref to PlayerGameStats)  
  * UniqueConstraint('team\_id', 'jersey\_number', name='uq\_player\_team\_jersey')  
  * UniqueConstraint('team\_id', 'name', name='uq\_player\_team\_name')  
* **4.3. Game Model (corresponds to Games Table)**  
  * id (Integer, primary\_key=True, autoincrement=True)  
  * date (String, nullable=False) *(Store as YYYY-MM-DD string or use SQLAlchemy Date type)*  
  * playing\_team\_id (Integer, ForeignKey('teams.id'), nullable=False)  
  * opponent\_team\_id (Integer, ForeignKey('teams.id'), nullable=False)  
  * playing\_team (relationship to Team, foreign\_keys=\[playing\_team\_id\])  
  * opponent\_team (relationship to Team, foreign\_keys=\[opponent\_team\_id\])  
  * player\_game\_stats (relationship backref to PlayerGameStats)  
* **4.4. PlayerGameStats Model (corresponds to PlayerGameStats Table)**  
  * id (Integer, primary\_key=True, autoincrement=True)  
  * game\_id (Integer, ForeignKey('games.id'), nullable=False)  
  * player\_id (Integer, ForeignKey('players.id'), nullable=False)  
  * fouls (Integer, nullable=False, default=0)  
  * total\_ftm (Integer, nullable=False, default=0)  
  * total\_fta (Integer, nullable=False, default=0)  
  * total\_2pm (Integer, nullable=False, default=0)  
  * total\_2pa (Integer, nullable=False, default=0)  
  * total\_3pm (Integer, nullable=False, default=0)  
  * total\_3pa (Integer, nullable=False, default=0)  
  * game (relationship to Game)  
  * player (relationship to Player)  
  * quarter\_stats (relationship backref to PlayerQuarterStats)  
  * UniqueConstraint('game\_id', 'player\_id', name='uq\_player\_game')  
* **4.5. PlayerQuarterStats Model (corresponds to PlayerQuarterStats Table)**  
  * id (Integer, primary\_key=True, autoincrement=True)  
  * player\_game\_stat\_id (Integer, ForeignKey('player\_game\_stats.id'), nullable=False)  
  * quarter\_number (Integer, nullable=False) \# Add CheckConstraint in SQLAlchemy  
  * ftm (Integer, nullable=False, default=0)  
  * fta (Integer, nullable=False, default=0)  
  * fg2m (Integer, nullable=False, default=0)  
  * fg2a (Integer, nullable=False, default=0)  
  * fg3m (Integer, nullable=False, default=0)  
  * fg3a (Integer, nullable=False, default=0)  
  * player\_game\_stat (relationship to PlayerGameStats)  
  * UniqueConstraint('player\_game\_stat\_id', 'quarter\_number', name='uq\_player\_game\_quarter')  
  * CheckConstraint('quarter\_number \>= 1 AND quarter\_number \<= 4', name='check\_quarter\_number')

**5\. Input Mechanism & Data Processing**

* **5.1. Web UI Data Entry Form (app/web\_ui/templates/form.html):**  
  * (Description unchanged)  
* **5.2. Form Submission Handling (in Flask routes defined in app/web\_ui/routes.py):**  
  * Receives POST data.  
  * Validates input data using Pydantic v2 models defined in app/web\_ui/schemas.py.  
  * If validation fails, re-renders the form with error messages.  
  * If validation succeeds, extracts game info, calls game\_service.py.  
  * Iterates validated player data, calls player\_service.py and stats\_entry\_service.py.  
  * Redirects to a success page or re-renders the form with a success message.  
* **5.3. Shot String Parsing (in app/utils/input\_parser.py):**  
  * parse\_quarter\_shot\_string(shot\_string: str) \-\> dict (Logic unchanged).  
* **5.4. Storing Data (in app/services/stats\_entry\_service.py using CRUD functions from app/data\_access/crud/):**  
  * (Logic unchanged conceptually, but now calls specific CRUD functions that use SQLAlchemy objects).

6\. Output Display (Reporting \- app/reports/report\_generator.py)  
(Unchanged for now. CLI or simple CSV export triggered via run\_cli.py.)  
7\. Data Management: Output, Caching, Backups, Integrity  
(Unchanged)  
8\. Future Considerations (Beyond Initial KISS Scope)  
(Unchanged)  
**Dependencies to include in pyproject.toml:**

* Flask (for the web UI)  
* SQLAlchemy (for ORM)  
* Pydantic (version 2.x, for data validation)  
* python-dotenv (for managing configuration, optional but good practice)  
* tabulate (for CLI reports)  
* Alembic (optional, for database migrations if schema evolves significantly)  
* Typer or Click (optional, for a more structured run\_cli.py)