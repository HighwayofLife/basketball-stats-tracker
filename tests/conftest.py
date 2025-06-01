"""
Common test fixtures for the basketball stats tracker application.
"""

import os
import tempfile
from collections.abc import Generator
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.data_access.models import Base

# Set up JWT secret for tests
if "JWT_SECRET_KEY" not in os.environ:
    os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-that-is-long-enough-for-validation-purposes"


@pytest.fixture
def test_db_url() -> str:
    """
    Returns a database URL for a temporary in-memory SQLite database.
    """
    return "sqlite:///:memory:"


@pytest.fixture
def test_db_file_url() -> Generator[str, None, None]:
    """
    Returns a database URL for a temporary file-based SQLite database.
    Use this for integration tests with FastAPI TestClient.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
        db_url = f"sqlite:///{temp_db.name}"
        yield db_url
        # Clean up the temp file
        os.unlink(temp_db.name)


@pytest.fixture
def test_shot_mapping() -> dict[str, dict[str, Any]]:
    """
    Returns a shot mapping for testing.
    """
    return {
        "1": {"type": "FT", "made": True, "points": 1},
        "x": {"type": "FT", "made": False, "points": 0},
        "2": {"type": "2P", "made": True, "points": 2},
        "-": {"type": "2P", "made": False, "points": 0},
        "3": {"type": "3P", "made": True, "points": 3},
        "/": {"type": "3P", "made": False, "points": 0},
    }


@pytest.fixture
def db_engine(test_db_url: str):
    """
    Creates a SQLAlchemy engine for an in-memory database.
    """
    engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(db_engine) -> Generator[Session, None, None]:
    """
    Creates a SQLAlchemy session for database operations during tests.
    """
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_db_file_engine(test_db_file_url: str):
    """
    Creates a SQLAlchemy engine for a file-based database.
    Use this for integration tests with FastAPI TestClient.
    """

    engine = create_engine(test_db_file_url, connect_args={"check_same_thread": False})

    # Create all tables using metadata (includes soft delete columns)
    Base.metadata.drop_all(engine)  # Clean slate
    Base.metadata.create_all(engine)

    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def test_db_file_session(test_db_file_engine) -> Generator[Session, None, None]:
    """
    Creates a SQLAlchemy session for file-based database operations during integration tests.
    """
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_file_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_teams() -> list[dict[str, str]]:
    """
    Returns sample team data for testing.
    """
    return [{"name": "Team A"}, {"name": "Team B"}]


@pytest.fixture
def sample_players() -> list[dict[str, Any]]:
    """
    Returns sample player data for testing.
    """
    return [
        {"name": "Player One", "jersey_number": "10", "team_name": "Team A"},
        {"name": "Player Two", "jersey_number": "23", "team_name": "Team A"},
        {"name": "Player Alpha", "jersey_number": "5", "team_name": "Team B"},
        {"name": "Player Beta", "jersey_number": "15", "team_name": "Team B"},
    ]


@pytest.fixture
def sample_game() -> dict[str, Any]:
    """
    Returns sample game data for testing.
    """
    return {"date": "2025-05-01", "playing_team": "Team A", "opponent_team": "Team B"}


@pytest.fixture
def sample_player_stats() -> list[dict[str, Any]]:
    """
    Returns sample player game statistics for testing.
    """
    return [
        {
            "team_name": "Team A",
            "player_jersey": "10",
            "player_name": "Player One",
            "fouls": 2,
            "qt1_shots": "22-1x",
            "qt2_shots": "3/2",
            "qt3_shots": "11",
            "qt4_shots": "",
        },
        {
            "team_name": "Team A",
            "player_jersey": "23",
            "player_name": "Player Two",
            "fouls": 3,
            "qt1_shots": "12",
            "qt2_shots": "x",
            "qt3_shots": "-/",
            "qt4_shots": "22",
        },
        {
            "team_name": "Team B",
            "player_jersey": "5",
            "player_name": "Player Alpha",
            "fouls": 1,
            "qt1_shots": "x",
            "qt2_shots": "11",
            "qt3_shots": "",
            "qt4_shots": "33-",
        },
        {
            "team_name": "Team B",
            "player_jersey": "15",
            "player_name": "Player Beta",
            "fouls": 4,
            "qt1_shots": "2//1",
            "qt2_shots": "2",
            "qt3_shots": "x",
            "qt4_shots": "1",
        },
    ]


@pytest.fixture
def sample_game_csv_content() -> str:
    """
    Returns sample CSV content for game stats import testing.
    """
    return """Home,Team A
Visitor,Team B
Date,2025-05-01
Team,Jersey Number,Player Name,Fouls,QT1,QT2,QT3,QT4
Team A,10,Player One,2,22-1x,3/2,11,
Team A,23,Player Two,3,12,x,-/,22
Team B,5,Player Alpha,1,x,11,,33-
Team B,15,Player Beta,4,2//1,2,x,1"""


@pytest.fixture
def sample_game_csv_file(sample_game_csv_content: str) -> Generator[str, None, None]:
    """
    Creates a temporary CSV file with sample game data for testing.
    """
    _, temp_file_path = tempfile.mkstemp(suffix=".csv")
    with open(temp_file_path, "w") as f:
        f.write(sample_game_csv_content)
    yield temp_file_path
    os.unlink(temp_file_path)


@pytest.fixture
def parsed_quarter_stats() -> dict[str, dict[str, int]]:
    """
    Returns pre-parsed quarter stats for testing.
    """
    return {
        "22-1x": {"ftm": 1, "fta": 2, "fg2m": 2, "fg2a": 3, "fg3m": 0, "fg3a": 0},
        "3/2": {"ftm": 0, "fta": 0, "fg2m": 1, "fg2a": 1, "fg3m": 1, "fg3a": 2},
        "11": {"ftm": 2, "fta": 2, "fg2m": 0, "fg2a": 0, "fg3m": 0, "fg3a": 0},
        "": {"ftm": 0, "fta": 0, "fg2m": 0, "fg2a": 0, "fg3m": 0, "fg3a": 0},
        "12": {"ftm": 1, "fta": 1, "fg2m": 1, "fg2a": 1, "fg3m": 0, "fg3a": 0},
        "x": {"ftm": 0, "fta": 1, "fg2m": 0, "fg2a": 0, "fg3m": 0, "fg3a": 0},
        "-/": {"ftm": 0, "fta": 0, "fg2m": 0, "fg2a": 1, "fg3m": 0, "fg3a": 1},
        "2//1": {"ftm": 1, "fta": 1, "fg2m": 1, "fg2a": 1, "fg3m": 0, "fg3a": 2},
        "33-": {"ftm": 0, "fta": 0, "fg2m": 0, "fg2a": 1, "fg3m": 2, "fg3a": 2},
    }
