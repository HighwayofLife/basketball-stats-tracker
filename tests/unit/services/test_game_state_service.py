"""
Test module for the GameStateService.
"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from app.data_access.models import (
    ActiveRoster,
    Game,
    GameEvent,
    GameState,
    Player,
    PlayerGameStats,
    PlayerQuarterStats,
    Team,
)
from app.services.game_state_service import GameStateService


@pytest.fixture
def mock_db_session():
    """Create a mock database session for unit testing."""
    return MagicMock()


class TestGameStateService:
    """Tests for the GameStateService."""

    def test_init(self, mock_db_session):
        """Test initializing the game state service."""
        service = GameStateService(mock_db_session)
        assert service.session == mock_db_session

    def test_create_game(self, mock_db_session):
        """Test creating a new game."""
        service = GameStateService(mock_db_session)

        # Mock database operations
        mock_db_session.add = MagicMock()
        mock_db_session.flush = MagicMock()
        mock_db_session.commit = MagicMock()

        game = service.create_game("2025-05-01", 1, 2, "Home Court", "19:00", "Test game")

        # Verify game creation
        assert game.date.strftime("%Y-%m-%d") == "2025-05-01"
        assert game.playing_team_id == 1
        assert game.opponent_team_id == 2
        assert game.location == "Home Court"
        assert game.scheduled_time.strftime("%H:%M") == "19:00"
        assert game.notes == "Test game"

        # Verify database calls
        assert mock_db_session.add.call_count == 2  # Game and GameState
        mock_db_session.flush.assert_called_once()
        mock_db_session.commit.assert_called_once()

    def test_create_game_minimal(self, mock_db_session):
        """Test creating a game with minimal required fields."""
        service = GameStateService(mock_db_session)

        # Mock database operations
        mock_db_session.add = MagicMock()
        mock_db_session.flush = MagicMock()
        mock_db_session.commit = MagicMock()

        game = service.create_game("2025-05-01", 1, 2)

        assert game.date.strftime("%Y-%m-%d") == "2025-05-01"
        assert game.playing_team_id == 1
        assert game.opponent_team_id == 2
        assert game.location is None
        assert game.scheduled_time is None
        assert game.notes is None

    def test_start_game(self):
        """Test starting a game."""
        # Create a mock session
        mock_session = MagicMock()
        service = GameStateService(mock_session)

        # Mock game and game state
        mock_game = Game(id=1, playing_team_id=1, opponent_team_id=2)
        mock_game_state = GameState(game_id=1, is_live=False, is_final=False)

        # Configure the mock query chain
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.side_effect = [mock_game, mock_game_state]
        mock_session.query.return_value = mock_query

        # Mock helper methods
        service._check_in_players = MagicMock()

        result = service.start_game(1, [1, 2, 3, 4, 5], [6, 7, 8, 9, 10])

        assert result.is_live is True
        assert result.current_quarter == 1
        service._check_in_players.assert_any_call(1, 1, [1, 2, 3, 4, 5], is_starter=True)
        service._check_in_players.assert_any_call(1, 2, [6, 7, 8, 9, 10], is_starter=True)
        mock_session.add.assert_called()  # For GameEvent
        mock_session.commit.assert_called_once()

    def test_start_game_not_found(self):
        """Test starting a game that doesn't exist."""
        # Create a mock session
        mock_session = MagicMock()
        service = GameStateService(mock_session)

        # Configure mock to return None (game not found)
        mock_session.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="Game 1 not found"):
            service.start_game(1, [1, 2, 3, 4, 5], [6, 7, 8, 9, 10])

    def test_start_game_already_live(self):
        """Test starting a game that's already in progress."""
        # Create a mock session
        mock_session = MagicMock()
        service = GameStateService(mock_session)

        # Mock game and game state
        mock_game = Game(id=1, playing_team_id=1, opponent_team_id=2)
        mock_game_state = GameState(game_id=1, is_live=True, is_final=False)

        mock_session.query.return_value.filter.return_value.first.side_effect = [mock_game, mock_game_state]

        with pytest.raises(ValueError, match="Game is already in progress"):
            service.start_game(1, [1, 2, 3, 4, 5], [6, 7, 8, 9, 10])

    def test_start_game_already_final(self, mock_db_session):
        """Test starting a game that's already finished."""
        service = GameStateService(mock_db_session)

        # Mock game and game state
        mock_game = Game(id=1, playing_team_id=1, opponent_team_id=2)
        mock_game_state = GameState(game_id=1, is_live=False, is_final=True)

        mock_db_session.query.return_value.filter.return_value.first.side_effect = [mock_game, mock_game_state]

        with pytest.raises(ValueError, match="Game has already ended"):
            service.start_game(1, [1, 2, 3, 4, 5], [6, 7, 8, 9, 10])

    def test_record_shot_made(self, mock_db_session):
        """Test recording a made shot."""
        service = GameStateService(mock_db_session)

        # Mock game state
        mock_game_state = GameState(game_id=1, is_live=True, current_quarter=1)
        service._get_game_state = MagicMock(return_value=mock_game_state)
        service._get_player_team_id = MagicMock(return_value=1)
        service._update_player_stats = MagicMock()

        mock_db_session.add = MagicMock()
        mock_db_session.commit = MagicMock()

        result = service.record_shot(1, 5, "2pt", True)

        assert result["player_id"] == 5
        assert result["shot_type"] == "2pt"
        assert result["made"] is True
        assert result["quarter"] == 1

        service._update_player_stats.assert_called_once_with(1, 5, 1, "2pt", True)
        mock_db_session.add.assert_called()
        mock_db_session.commit.assert_called_once()

    def test_record_shot_game_not_live(self, mock_db_session):
        """Test recording a shot when game is not live."""
        service = GameStateService(mock_db_session)

        # Mock game state that's not live
        mock_game_state = GameState(game_id=1, is_live=False, current_quarter=1)
        service._get_game_state = MagicMock(return_value=mock_game_state)

        with pytest.raises(ValueError, match="Game is not in progress"):
            service.record_shot(1, 5, "2pt", True)

    def test_record_foul(self, mock_db_session):
        """Test recording a foul."""
        service = GameStateService(mock_db_session)

        # Mock game state
        mock_game_state = GameState(game_id=1, is_live=True, current_quarter=2)
        service._get_game_state = MagicMock(return_value=mock_game_state)
        service._get_player_team_id = MagicMock(return_value=1)

        # Mock player stats
        mock_stats = PlayerGameStats(game_id=1, player_id=5, fouls=1)
        service._get_or_create_player_game_stats = MagicMock(return_value=mock_stats)

        mock_db_session.add = MagicMock()
        mock_db_session.commit = MagicMock()

        result = service.record_foul(1, 5, "technical")

        assert result["player_id"] == 5
        assert result["foul_type"] == "technical"
        assert result["quarter"] == 2
        assert result["total_fouls"] == 2  # Was 1, now 2
        assert mock_stats.fouls == 2

    def test_substitute_players(self, mock_db_session):
        """Test substituting players."""
        service = GameStateService(mock_db_session)

        # Mock game state
        mock_game_state = GameState(game_id=1, is_live=True, current_quarter=3)
        service._get_game_state = MagicMock(return_value=mock_game_state)
        service._check_in_players = MagicMock()

        # Mock active roster entry
        mock_roster = ActiveRoster(game_id=1, player_id=5, checked_out_at=None)
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_roster

        mock_db_session.add = MagicMock()
        mock_db_session.commit = MagicMock()

        result = service.substitute_players(1, 1, [5], [15])

        assert result["team_id"] == 1
        assert result["players_out"] == [5]
        assert result["players_in"] == [15]
        assert result["quarter"] == 3

        # Verify player was checked out
        assert mock_roster.checked_out_at is not None
        service._check_in_players.assert_called_once_with(1, 1, [15])

    def test_end_quarter(self, mock_db_session):
        """Test ending a quarter."""
        service = GameStateService(mock_db_session)

        # Mock game state
        mock_game_state = GameState(game_id=1, is_live=True, current_quarter=2)
        service._get_game_state = MagicMock(return_value=mock_game_state)

        mock_db_session.add = MagicMock()
        mock_db_session.commit = MagicMock()

        result = service.end_quarter(1)

        assert result.current_quarter == 3
        mock_db_session.add.assert_called()  # For GameEvent
        mock_db_session.commit.assert_called_once()

    def test_end_quarter_past_fourth(self, mock_db_session):
        """Test ending quarter when already in 4th quarter."""
        service = GameStateService(mock_db_session)

        # Mock game state in 4th quarter
        mock_game_state = GameState(game_id=1, is_live=True, current_quarter=4)
        service._get_game_state = MagicMock(return_value=mock_game_state)

        with pytest.raises(ValueError, match="Cannot advance past 4th quarter"):
            service.end_quarter(1)

    def test_finalize_game(self, mock_db_session):
        """Test finalizing a game."""
        service = GameStateService(mock_db_session)

        # Mock game state and game
        mock_game_state = GameState(game_id=1, is_live=True, is_final=False, current_quarter=4)
        mock_team_a = Team(id=1, name="Team A")
        mock_team_b = Team(id=2, name="Team B")
        mock_game = Game(id=1, playing_team_id=1, opponent_team_id=2)
        mock_game.playing_team = mock_team_a
        mock_game.opponent_team = mock_team_b

        service._get_game_state = MagicMock(return_value=mock_game_state)
        service._calculate_team_score = MagicMock(side_effect=[85, 78])

        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_game
        mock_db_session.add = MagicMock()
        mock_db_session.commit = MagicMock()

        result = service.finalize_game(1)

        assert result["game_id"] == 1
        assert result["state"] == "final"
        assert result["home_team"] == "Team A"
        assert result["away_team"] == "Team B"
        assert result["home_score"] == 85
        assert result["away_score"] == 78

        assert mock_game_state.is_live is False
        assert mock_game_state.is_final is True

    def test_finalize_game_already_final(self, mock_db_session):
        """Test finalizing a game that's already final."""
        service = GameStateService(mock_db_session)

        # Mock game state that's already final
        mock_game_state = GameState(game_id=1, is_live=False, is_final=True)
        service._get_game_state = MagicMock(return_value=mock_game_state)

        with pytest.raises(ValueError, match="Game is already finalized"):
            service.finalize_game(1)

    def test_get_live_game_state(self, mock_db_session):
        """Test getting live game state."""
        service = GameStateService(mock_db_session)

        # Mock game state and game
        mock_game_state = GameState(
            game_id=1,
            current_quarter=2,
            is_live=True,
            is_final=False,
            home_timeouts_remaining=3,
            away_timeouts_remaining=4,
        )
        mock_team_a = Team(id=1, name="Team A")
        mock_team_b = Team(id=2, name="Team B")
        mock_game = Game(id=1, playing_team_id=1, opponent_team_id=2)
        mock_game.playing_team = mock_team_a
        mock_game.opponent_team = mock_team_b

        service._get_game_state = MagicMock(return_value=mock_game_state)
        service._get_active_players = MagicMock(return_value={"home": [], "away": []})
        service._calculate_team_score = MagicMock(side_effect=[42, 38])

        # Mock recent events
        mock_event = GameEvent(
            id=1,
            event_type="shot",
            player_id=5,
            team_id=1,
            quarter=2,
            timestamp=datetime(2025, 5, 23, 19, 30),
            details={"shot_type": "2pt", "made": True},
        )

        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_game
        (
            mock_db_session.query.return_value.filter.return_value.order_by.return_value
            .limit.return_value.all.return_value
        ) = [mock_event]

        result = service.get_live_game_state(1)

        assert result["game_state"]["game_id"] == 1
        assert result["game_state"]["current_quarter"] == 2
        assert result["game_state"]["is_live"] is True
        assert result["game_state"]["home_score"] == 42
        assert result["game_state"]["away_score"] == 38
        assert result["game_state"]["home_timeouts"] == 3
        assert result["game_state"]["away_timeouts"] == 4
        assert len(result["recent_events"]) == 1
        assert result["recent_events"][0]["type"] == "shot"

    def test_undo_last_event_shot(self, mock_db_session):
        """Test undoing a shot event."""
        service = GameStateService(mock_db_session)

        # Mock last event
        mock_event = GameEvent(
            id=1, game_id=1, event_type="shot", player_id=5, quarter=2, details={"shot_type": "2pt", "made": True}
        )

        mock_db_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_event
        service._undo_shot = MagicMock()

        mock_db_session.add = MagicMock()
        mock_db_session.delete = MagicMock()
        mock_db_session.commit = MagicMock()

        result = service.undo_last_event(1)

        service._undo_shot.assert_called_once_with(mock_event)
        mock_db_session.delete.assert_called_once_with(mock_event)
        assert result["undone_event"]["id"] == 1
        assert result["undone_event"]["type"] == "shot"

    def test_undo_last_event_no_events(self, mock_db_session):
        """Test undoing when there are no events."""
        service = GameStateService(mock_db_session)

        mock_db_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = None

        with pytest.raises(ValueError, match="No events to undo"):
            service.undo_last_event(1)

    def test_get_game_state_not_found(self, mock_db_session):
        """Test getting game state that doesn't exist."""
        service = GameStateService(mock_db_session)

        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="Game state for game 1 not found"):
            service._get_game_state(1)

    def test_get_player_team_id(self, mock_db_session):
        """Test getting player team ID."""
        service = GameStateService(mock_db_session)

        mock_player = Player(id=5, team_id=1)
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_player

        team_id = service._get_player_team_id(5)
        assert team_id == 1

    def test_get_player_team_id_not_found(self, mock_db_session):
        """Test getting team ID for non-existent player."""
        service = GameStateService(mock_db_session)

        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="Player 5 not found"):
            service._get_player_team_id(5)

    def test_update_player_stats_2pt_made(self, mock_db_session):
        """Test updating player stats for a made 2-pointer."""
        service = GameStateService(mock_db_session)

        # Mock stats objects
        mock_game_stats = PlayerGameStats(id=1, total_2pm=0, total_2pa=0)
        mock_quarter_stats = PlayerQuarterStats(player_game_stat_id=1, quarter_number=1, fg2m=0, fg2a=0)

        service._get_or_create_player_game_stats = MagicMock(return_value=mock_game_stats)
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_quarter_stats
        mock_db_session.add = MagicMock()

        service._update_player_stats(1, 5, 1, "2pt", True)

        assert mock_game_stats.total_2pm == 1
        assert mock_game_stats.total_2pa == 1
        assert mock_quarter_stats.fg2m == 1
        assert mock_quarter_stats.fg2a == 1

    def test_update_player_stats_3pt_missed(self, mock_db_session):
        """Test updating player stats for a missed 3-pointer."""
        service = GameStateService(mock_db_session)

        # Mock stats objects
        mock_game_stats = PlayerGameStats(id=1, total_3pm=0, total_3pa=0)
        mock_quarter_stats = PlayerQuarterStats(player_game_stat_id=1, quarter_number=2, fg3m=0, fg3a=0)

        service._get_or_create_player_game_stats = MagicMock(return_value=mock_game_stats)
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_quarter_stats
        mock_db_session.add = MagicMock()

        service._update_player_stats(1, 5, 2, "3pt", False)

        assert mock_game_stats.total_3pm == 0
        assert mock_game_stats.total_3pa == 1
        assert mock_quarter_stats.fg3m == 0
        assert mock_quarter_stats.fg3a == 1

    def test_update_player_stats_ft_made(self, mock_db_session):
        """Test updating player stats for a made free throw."""
        service = GameStateService(mock_db_session)

        # Mock stats objects
        mock_game_stats = PlayerGameStats(id=1, total_ftm=0, total_fta=0)
        mock_quarter_stats = PlayerQuarterStats(player_game_stat_id=1, quarter_number=3, ftm=0, fta=0)

        service._get_or_create_player_game_stats = MagicMock(return_value=mock_game_stats)
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_quarter_stats
        mock_db_session.add = MagicMock()

        service._update_player_stats(1, 5, 3, "ft", True)

        assert mock_game_stats.total_ftm == 1
        assert mock_game_stats.total_fta == 1
        assert mock_quarter_stats.ftm == 1
        assert mock_quarter_stats.fta == 1

    def test_calculate_team_score(self, mock_db_session):
        """Test calculating team score."""
        service = GameStateService(mock_db_session)

        # Mock players
        mock_players = [Player(id=1, team_id=1), Player(id=2, team_id=1)]

        # Mock stats
        mock_stats = [
            PlayerGameStats(id=1, player_id=1, total_ftm=2, total_2pm=5, total_3pm=3),
            PlayerGameStats(id=2, player_id=2, total_ftm=1, total_2pm=3, total_3pm=1),
        ]

        mock_db_session.query.return_value.filter.return_value.all.side_effect = [mock_players, mock_stats]

        score = service._calculate_team_score(1, 1)

        # Player 1: 2 + (5*2) + (3*3) = 2 + 10 + 9 = 21
        # Player 2: 1 + (3*2) + (1*3) = 1 + 6 + 3 = 10
        # Total: 31
        assert score == 31
