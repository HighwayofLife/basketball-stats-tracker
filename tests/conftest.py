"""
Common test fixtures for the basketball stats tracker application.
"""

import io
import os
import tempfile
from collections.abc import Generator
from typing import Any

import pytest
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Import tempfile at the top level

# Set up JWT secret for tests BEFORE importing models
if "JWT_SECRET_KEY" not in os.environ:
    os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-that-is-long-enough-for-validation-purposes"

# Set up test upload directory to avoid overwriting real uploads
if "UPLOAD_DIR" not in os.environ:
    os.environ["UPLOAD_DIR"] = "/tmp/test_uploads"

# Import all models to ensure they're registered with Base.metadata
from app.auth.models import User  # noqa: F401
from app.data_access.models import (  # noqa: F401
    AuditLog,
    Base,
    Game,
    GameState,
    Player,
    PlayerGameStats,
    PlayerQuarterStats,
    PlayerSeasonStats,
    ScheduledGame,
    Season,
    Team,
    TeamSeasonStats,
)


@pytest.fixture(autouse=True)
def reset_app_state_globally():
    """
    Globally reset FastAPI app state before each test.
    This prevents any test from leaving the app in a bad state that affects other tests.
    """
    try:
        from app.web_ui.api import app

        # Store original state
        original_overrides = app.dependency_overrides.copy()

        # Clear any existing overrides before test
        app.dependency_overrides.clear()

        # Clear team logo cache to prevent unit test mocks from affecting integration tests
        try:
            from app.web_ui.templates_config import clear_team_logo_cache

            clear_team_logo_cache()
        except ImportError:
            pass

        yield

        # Restore original state after test
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)

        # Clear team logo cache again after test
        try:
            from app.web_ui.templates_config import clear_team_logo_cache

            clear_team_logo_cache()
        except ImportError:
            pass
    except ImportError:
        # If the app can't be imported (e.g., some tests don't need it), just pass
        yield


@pytest.fixture
def test_db_url() -> str:
    """
    Returns a database URL for a temporary in-memory SQLite database.
    """
    return "sqlite:///:memory:"


@pytest.fixture(scope="class")
def test_db_file_url(request) -> Generator[str, None, None]:
    """
    Returns a database URL for a temporary file-based SQLite database.
    DEPRECATED: Use integration_db_engine with appropriate markers instead.
    """
    # Create a unique database name based on the test class to prevent conflicts
    class_name = request.cls.__name__ if request.cls else "default"
    with tempfile.NamedTemporaryFile(prefix=f"test_db_{class_name}_", suffix=".db", delete=False) as temp_db:
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


# ============================================================================
# UNIFIED DATABASE FIXTURES
# ============================================================================
# These fixtures provide consistent database setup across all test types.
# Unit tests should use unit_db_session (in-memory, fast)
# Integration tests should use integration_db_session (file-based, persistent)
# ============================================================================


@pytest.fixture
def db_engine(test_db_url: str):
    """
    Creates a SQLAlchemy engine for an in-memory database.
    DEPRECATED: Use unit_db_engine or integration_db_engine instead.
    """
    engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(db_engine) -> Generator[Session, None, None]:
    """
    Creates a SQLAlchemy session for database operations during tests.
    DEPRECATED: Use unit_db_session or integration_db_session instead.
    """
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def unit_db_engine():
    """
    Creates an in-memory SQLite engine for fast unit tests.
    This should be used for all unit tests that need database access.
    """
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def unit_db_session(unit_db_engine) -> Generator[Session, None, None]:
    """
    Creates a database session for unit tests using in-memory SQLite.
    Fast, isolated, and perfect for testing individual components.
    """
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=unit_db_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="class")
def integration_db_engine(request):
    """
    Creates a database engine for integration tests.
    Uses PostgreSQL if DATABASE_URL is set (container environment),
    otherwise uses file-based SQLite for local development.
    """
    # Check if we're in a container environment with PostgreSQL
    database_url = os.environ.get("DATABASE_URL")
    if database_url and database_url.startswith("postgresql://"):
        # Use PostgreSQL for integration tests in container
        engine = create_engine(database_url)
        # For PostgreSQL, run Alembic migrations to ensure all tables exist
        from alembic import command
        from alembic.config import Config

        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        yield engine
        # Don't drop tables on cleanup for PostgreSQL
    else:
        # Use file-based SQLite for local development
        # Create a unique database name based on the test class to prevent conflicts
        class_name = request.cls.__name__ if request.cls else "default"
        with tempfile.NamedTemporaryFile(
            prefix=f"test_integration_{class_name}_", suffix=".db", delete=False
        ) as temp_db:
            db_path = temp_db.name
            db_url = f"sqlite:///{db_path}"

        try:
            engine = create_engine(db_url, connect_args={"check_same_thread": False})

            # Create all tables including those from auth models
            # This ensures both main models and auth models are created
            Base.metadata.create_all(engine)

            yield engine
        finally:
            # Clean up the temp file
            try:
                engine.dispose()
                os.unlink(db_path)
            except (OSError, FileNotFoundError):
                pass  # File might already be deleted


@pytest.fixture(scope="class")
def integration_db_session(integration_db_engine) -> Generator[Session, None, None]:
    """
    Creates a database session for integration tests using file-based SQLite.
    Use this for testing complete workflows and API endpoints.
    """
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=integration_db_engine)
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


# ============================================================================
# TEST DATA FACTORY FIXTURES
# ============================================================================
# These fixtures provide consistent test data creation across all tests.
# Use factories instead of hardcoded data for flexibility and consistency.
# ============================================================================


@pytest.fixture(scope="class")
def team_factory():
    """
    Factory for creating team test data with consistent defaults.

    Usage:
        team = team_factory()  # Creates Team A
        team = team_factory("Lakers")  # Creates Lakers
        team = team_factory("Warriors", id=2)  # Creates Warriors with specific ID
    """

    def _create_team(name: str = "Team A", **kwargs) -> dict[str, Any]:
        team_data = {"name": name}
        team_data.update(kwargs)
        return team_data

    return _create_team


@pytest.fixture(scope="class")
def player_factory():
    """
    Factory for creating player test data with consistent defaults.

    Usage:
        player = player_factory()  # Creates Player One
        player = player_factory("LeBron James", jersey="23", team_name="Lakers")
    """

    def _create_player(
        name: str = "Player One",
        jersey_number: str = "10",
        team_name: str = "Team A",
        position: str = "Forward",
        height: str = "6'8\"",
        weight: int = 220,
        year: str = "Senior",
        **kwargs,
    ) -> dict[str, Any]:
        player_data = {
            "name": name,
            "jersey_number": jersey_number,
            "team_name": team_name,
            "position": position,
            "height": height,
            "weight": weight,
            "year": year,
        }
        player_data.update(kwargs)
        return player_data

    return _create_player


@pytest.fixture(scope="class")
def game_factory():
    """
    Factory for creating game test data with consistent defaults.

    Usage:
        game = game_factory()  # Creates game on 2025-05-01
        game = game_factory(date="2025-06-15", home_team="Lakers", away_team="Warriors")
    """

    def _create_game(
        date: str = "2025-05-01",
        playing_team: str = "Team A",
        opponent_team: str = "Team B",
        home_score: int | None = None,
        away_score: int | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        game_data = {
            "date": date,
            "playing_team": playing_team,
            "opponent_team": opponent_team,
        }
        if home_score is not None:
            game_data["home_score"] = home_score
        if away_score is not None:
            game_data["away_score"] = away_score
        game_data.update(kwargs)
        return game_data

    return _create_game


@pytest.fixture(scope="class")
def player_stats_factory():
    """
    Factory for creating player game statistics with consistent defaults.

    Usage:
        stats = player_stats_factory()  # Creates basic stats
        stats = player_stats_factory(qt1_shots="33-", qt2_shots="22-1x")
    """

    def _create_player_stats(
        team_name: str = "Team A",
        player_jersey: str = "10",
        player_name: str = "Player One",
        fouls: int = 2,
        qt1_shots: str = "22-1x",
        qt2_shots: str = "",
        qt3_shots: str = "",
        qt4_shots: str = "",
        **kwargs,
    ) -> dict[str, Any]:
        stats_data = {
            "team_name": team_name,
            "player_jersey": player_jersey,
            "player_name": player_name,
            "fouls": fouls,
            "qt1_shots": qt1_shots,
            "qt2_shots": qt2_shots,
            "qt3_shots": qt3_shots,
            "qt4_shots": qt4_shots,
        }
        stats_data.update(kwargs)
        return stats_data

    return _create_player_stats


# Legacy fixtures for backward compatibility - DEPRECATED
@pytest.fixture
def sample_teams(team_factory) -> list[dict[str, str]]:
    """
    DEPRECATED: Use team_factory instead.
    Returns sample team data for testing.
    """
    return [team_factory("Team A"), team_factory("Team B")]


@pytest.fixture
def sample_players(player_factory) -> list[dict[str, Any]]:
    """
    DEPRECATED: Use player_factory instead.
    Returns sample player data for testing.
    """
    return [
        player_factory("Player One", "10", "Team A"),
        player_factory("Player Two", "23", "Team A"),
        player_factory("Player Alpha", "5", "Team B"),
        player_factory("Player Beta", "15", "Team B"),
    ]


@pytest.fixture
def sample_game(game_factory) -> dict[str, Any]:
    """
    DEPRECATED: Use game_factory instead.
    Returns sample game data for testing.
    """
    return game_factory()


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


@pytest.fixture
def test_image_blue():
    """Create a blue test image for testing."""
    img = Image.new("RGB", (100, 100), color="blue")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG")
    img_bytes.seek(0)
    return ("test_logo.jpg", img_bytes, "image/jpeg")


@pytest.fixture
def test_image_green():
    """Create a green test image for testing."""
    img = Image.new("RGB", (100, 100), color="green")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)
    return ("test_logo.png", img_bytes, "image/png")


@pytest.fixture
def test_image_red():
    """Create a red test image for testing."""
    img = Image.new("RGB", (200, 200), color="red")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG")
    img_bytes.seek(0)
    return ("test_red.jpg", img_bytes, "image/jpeg")


@pytest.fixture
def oversized_test_image():
    """Create an oversized image file for testing."""
    import random

    # Create a large image with random noise that exceeds 5MB
    width, height = 2500, 2500
    img = Image.new("RGB", (width, height))

    # Fill with random colors to make compression harder and exceed 5MB
    pixels = []
    for _ in range(width * height):
        pixels.append((random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
    img.putdata(pixels)

    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG", quality=100)
    img_bytes.seek(0)
    return ("huge_logo.jpg", img_bytes, "image/jpeg")


@pytest.fixture
def test_image_factory():
    """
    Factory for creating test images with custom properties.

    Usage:
        image = test_image_factory(width=200, height=200, color="blue", format="PNG")
        image = test_image_factory(color="red")  # Uses defaults for other params
    """

    def _create_image(width=100, height=100, color="blue", format="JPEG"):
        img = Image.new("RGB", (width, height), color=color)
        img_bytes = io.BytesIO()
        img.save(img_bytes, format=format)
        img_bytes.seek(0)

        extension = "jpg" if format.upper() == "JPEG" else format.lower()
        filename = f"test_{color}_{width}x{height}.{extension}"
        mime_type = f"image/{format.lower()}"

        return (filename, img_bytes, mime_type)

    return _create_image


@pytest.fixture
def temp_image_file_factory(tmp_path):
    """
    Factory for creating temporary image files on disk.

    Usage:
        file_path = temp_image_file_factory(test_image_blue)
        file_path = temp_image_file_factory(custom_image_tuple)
    """

    def _create_temp_file(image_tuple, filename_override=None):
        filename, img_bytes, mime_type = image_tuple

        if filename_override:
            filename = filename_override

        file_path = tmp_path / filename

        # Reset BytesIO to beginning and write to file
        img_bytes.seek(0)
        with open(file_path, "wb") as f:
            f.write(img_bytes.read())

        # Reset BytesIO for any future use
        img_bytes.seek(0)

        return file_path

    return _create_temp_file


@pytest.fixture
def mock_upload_directory():
    """Provide a temporary directory for upload tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


# ============================================================================
# AUTHENTICATION FIXTURES
# ============================================================================
# Consistent authentication mocking across all tests
# ============================================================================


@pytest.fixture
def mock_admin_user():
    """
    Creates a mock admin user for testing authenticated endpoints.
    """
    return User(id=1, username="admin", email="admin@example.com", role="admin", is_active=True)


@pytest.fixture
def mock_regular_user():
    """
    Creates a mock regular user for testing role-based access.
    """
    return User(id=2, username="testuser", email="test@example.com", role="user", is_active=True)


@pytest.fixture
def authenticated_client(integration_db_session, mock_admin_user):
    """
    Creates a FastAPI test client with admin authentication.
    Use this for integration tests that require authentication.
    """
    from fastapi.testclient import TestClient

    from app.auth.dependencies import get_current_user
    from app.web_ui.api import app
    from app.web_ui.dependencies import get_db

    # Store original overrides
    original_overrides = app.dependency_overrides.copy()

    try:
        # Override dependencies
        def override_get_db():
            try:
                yield integration_db_session
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = lambda: mock_admin_user

        with TestClient(app) as client:
            yield client
    finally:
        # Restore original overrides
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)


@pytest.fixture
def unit_test_client(unit_db_session, unit_db_engine, mock_admin_user, monkeypatch, tmp_path):
    """
    Creates a FastAPI test client for unit tests with in-memory database.
    Each test gets a fresh, isolated database.
    """
    from contextlib import contextmanager

    from fastapi.testclient import TestClient

    from app.auth.dependencies import get_current_user
    from app.web_ui.api import app
    from app.web_ui.dependencies import get_db

    # Create a context manager that yields the unit test session
    @contextmanager
    def test_get_db_session():
        try:
            yield unit_db_session
        finally:
            pass

    # Set up a temporary upload directory for tests
    test_upload_dir = tmp_path / "test_uploads"
    test_upload_dir.mkdir(exist_ok=True)

    # Override the UPLOAD_DIR setting for tests
    from app import config

    monkeypatch.setattr(config.settings, "UPLOAD_DIR", str(test_upload_dir))

    # Monkey-patch the get_db_session function in modules that import it
    import app.data_access.db_session as db_session_module
    import app.web_ui.routers.admin as admin_module
    import app.web_ui.routers.auth as auth_module
    import app.web_ui.routers.games as games_module
    import app.web_ui.routers.pages as pages_module
    import app.web_ui.routers.players as players_module
    import app.web_ui.routers.reports as reports_module
    import app.web_ui.routers.teams as teams_module

    modules_to_patch = [
        db_session_module,
        pages_module,
        games_module,
        players_module,
        admin_module,
        auth_module,
        reports_module,
        teams_module,
    ]

    for module in modules_to_patch:
        if hasattr(module, "get_db_session"):
            monkeypatch.setattr(module, "get_db_session", test_get_db_session)

    # Store original overrides
    original_overrides = app.dependency_overrides.copy()

    try:
        # Override dependencies with unit test database
        # Important: Return the same session that has the test data
        def override_get_db():
            try:
                yield unit_db_session
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = lambda: mock_admin_user

        with TestClient(app) as client:
            yield client
    finally:
        # Restore original overrides
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)


@pytest.fixture
def unauthenticated_client(integration_db_session):
    """
    Creates a FastAPI test client without authentication.
    Use this for testing endpoints that don't require auth or to test auth failures.
    """
    from fastapi.testclient import TestClient

    from app.web_ui.api import app
    from app.web_ui.dependencies import get_db

    # Store original overrides
    original_overrides = app.dependency_overrides.copy()

    try:
        # Override only database dependency
        def override_get_db():
            try:
                yield integration_db_session
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db

        with TestClient(app) as client:
            yield client
    finally:
        # Restore original overrides
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)


@pytest.fixture
def unit_unauthenticated_client(unit_db_session):
    """
    Creates a FastAPI test client without authentication for unit tests.
    Use this for testing auth failures in unit tests.
    """
    from fastapi import HTTPException, status
    from fastapi.testclient import TestClient

    from app.auth.dependencies import get_current_user, require_admin
    from app.web_ui.api import app
    from app.web_ui.dependencies import get_db

    def mock_unauthenticated():
        """Mock unauthenticated state."""
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    # Store original overrides
    original_overrides = app.dependency_overrides.copy()

    try:
        app.dependency_overrides[get_db] = lambda: unit_db_session
        app.dependency_overrides[get_current_user] = mock_unauthenticated
        app.dependency_overrides[require_admin] = mock_unauthenticated

        with TestClient(app) as client:
            yield client
    finally:
        # Restore original overrides
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)


@pytest.fixture
def non_admin_client(unit_db_session, mock_regular_user):
    """
    Creates a FastAPI test client with non-admin user authentication for unit tests.
    Use this for testing admin access restrictions.
    """
    from fastapi import HTTPException, status
    from fastapi.testclient import TestClient

    from app.auth.dependencies import get_current_user, require_admin
    from app.web_ui.api import app
    from app.web_ui.dependencies import get_db

    def mock_require_admin():
        """Mock require_admin that fails for non-admin users."""
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    # Store original overrides
    original_overrides = app.dependency_overrides.copy()

    try:
        app.dependency_overrides[get_db] = lambda: unit_db_session
        app.dependency_overrides[get_current_user] = lambda: mock_regular_user
        app.dependency_overrides[require_admin] = mock_require_admin

        with TestClient(app) as client:
            yield client
    finally:
        # Restore original overrides
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)


@pytest.fixture
def auth_headers_factory():
    """
    Factory for creating JWT auth headers for different users.
    Use this for tests that need custom authentication headers.

    Usage:
        headers = auth_headers_factory(user_id=123)
        headers = auth_headers_factory(mock_user_object)
    """

    def _create_headers(user_or_id):
        from app.auth.jwt_handler import create_access_token

        user_id = user_or_id.id if hasattr(user_or_id, "id") else user_or_id

        token = create_access_token(data={"sub": str(user_id)})
        return {"Authorization": f"Bearer {token}"}

    return _create_headers


@pytest.fixture
def team_user_factory(integration_db_session):
    """
    Factory for creating team-specific users for security testing.
    Use this for tests that need users associated with specific teams.

    Usage:
        user = team_user_factory("testuser", "password", "user@example.com", team_id=1)
        admin = team_user_factory("admin", "pass", "admin@example.com", role="admin")
    """

    def _create_user(username, password, email, team_id=None, role="user"):
        from app.auth.models import UserRole

        user_role = UserRole.ADMIN if role == "admin" else UserRole.USER
        user = User(
            id=None,  # Auto-generated
            username=username,
            email=email,
            role=user_role,
            is_active=True,
            provider="local",
        )

        # Note: Password hashing would be handled by AuthService in real implementation
        # For testing, we'll create a simplified user object
        integration_db_session.add(user)
        integration_db_session.commit()
        integration_db_session.refresh(user)
        return user

    return _create_user


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "postgres: mark test to run with PostgreSQL database")
    config.addinivalue_line("markers", "sqlite_file: mark test to run with file-based SQLite")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "unit: mark test as unit test")


# ============================================================================
# SHARED DATABASE OBJECT FIXTURES
# ============================================================================
# These fixtures create actual database objects that can be shared across tests.
# Use these instead of creating custom fixtures in individual test files.
# ============================================================================


@pytest.fixture(scope="class")
def shared_test_team(integration_db_session):
    """
    Create a shared test team for integration tests.
    Use this instead of creating custom team fixtures in individual test files.
    """
    import uuid

    unique_suffix = str(uuid.uuid4())[:8]
    team = Team(
        name=f"SharedTestTeam_{unique_suffix}", display_name=f"Shared Test Team {unique_suffix}", is_deleted=False
    )
    integration_db_session.add(team)
    integration_db_session.commit()
    integration_db_session.refresh(team)
    return team


@pytest.fixture(scope="class")
def shared_test_player(integration_db_session, shared_test_team):
    """
    Create a shared test player for integration tests.
    Use this instead of creating custom player fixtures in individual test files.
    """

    player = Player(
        name="Shared Test Player",
        team_id=shared_test_team.id,
        jersey_number="99",
        position="PG",
        height=72,
        weight=180,
        year="Senior",
        is_active=True,
        is_substitute=False,
    )
    integration_db_session.add(player)
    integration_db_session.commit()
    integration_db_session.refresh(player)
    return player
