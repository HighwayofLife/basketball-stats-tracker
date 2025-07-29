"""Unit tests for the playoffs service."""

from datetime import date
from unittest.mock import MagicMock, Mock

import pytest
from sqlalchemy.orm import Session

from app.data_access.models import Game, ScheduledGame, Team
from app.services.playoffs_service import PlayoffsService


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    return MagicMock(spec=Session)


@pytest.fixture
def playoffs_service(mock_db_session):
    """Create a playoffs service instance with mock session."""
    return PlayoffsService(mock_db_session)


class TestPlayoffsService:
    """Test cases for PlayoffsService."""

    def test_get_playoff_bracket_no_games(self, playoffs_service, mock_db_session):
        """Test getting bracket when no playoff games exist."""
        # Mock empty query results for both completed and scheduled games
        mock_query = MagicMock()
        mock_query.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_query

        result = playoffs_service.get_playoff_bracket()

        # Verify both queries were executed (completed games and scheduled games)
        assert mock_db_session.execute.call_count == 2
        assert result["season"] == str(date.today().year)
        assert result["champion"] is None
        # Now we expect TBD placeholders instead of None/empty
        assert result["finals"] is not None
        assert result["finals"]["matchup"]["status"] == "tbd"
        assert result["finals"]["matchup"]["team1"]["team_name"] == "TBD"
        assert result["finals"]["matchup"]["team2"]["team_name"] == "TBD"
        assert len(result["semi_finals"]) == 2
        assert result["semi_finals"][0]["matchup"]["status"] == "tbd"
        assert result["semi_finals"][1]["matchup"]["status"] == "tbd"

    def test_get_playoff_bracket_with_games(self, playoffs_service, mock_db_session):
        """Test getting bracket with playoff games."""
        # Create mock teams
        team1 = Mock(spec=Team)
        team1.id = 1
        team1.name = "Team A"
        team2 = Mock(spec=Team)
        team2.id = 2
        team2.name = "Team B"
        team3 = Mock(spec=Team)
        team3.id = 3
        team3.name = "Team C"
        team4 = Mock(spec=Team)
        team4.id = 4
        team4.name = "Team D"

        # Create mock games
        final_game = Mock(
            spec=Game,
            id=101,
            date=date(2025, 3, 15),
            playing_team_id=1,
            opponent_team_id=2,
            playing_team_score=100,
            opponent_team_score=95,
            playing_team=team1,
            opponent_team=team2,
        )

        semi1 = Mock(
            spec=Game,
            id=102,
            date=date(2025, 3, 10),
            playing_team_id=1,
            opponent_team_id=3,
            playing_team_score=90,
            opponent_team_score=88,
            playing_team=team1,
            opponent_team=team3,
        )

        semi2 = Mock(
            spec=Game,
            id=103,
            date=date(2025, 3, 10),
            playing_team_id=2,
            opponent_team_id=4,
            playing_team_score=110,
            opponent_team_score=105,
            playing_team=team2,
            opponent_team=team4,
        )

        # Mock query results - first call returns completed games, second returns empty scheduled games
        completed_games_query = MagicMock()
        completed_games_query.scalars.return_value.all.return_value = [final_game, semi1, semi2]
        
        scheduled_games_query = MagicMock()
        scheduled_games_query.scalars.return_value.all.return_value = []
        
        mock_db_session.execute.side_effect = [completed_games_query, scheduled_games_query]

        result = playoffs_service.get_playoff_bracket()

        # Verify both queries were executed
        assert mock_db_session.execute.call_count == 2
        
        # Verify structure
        assert result["season"] == "2025"
        assert result["champion"] == {"team_id": 1, "team_name": "Team A"}
        assert result["finals"] is not None
        assert len(result["semi_finals"]) == 2

        # Verify finals
        finals = result["finals"]["matchup"]
        assert finals["game_id"] == 101
        assert finals["team1"]["team_name"] == "Team A"
        assert finals["team1"]["score"] == 100
        assert finals["team2"]["team_name"] == "Team B"
        assert finals["team2"]["score"] == 95

    def test_get_playoff_bracket_with_season_filter(self, playoffs_service, mock_db_session):
        """Test getting bracket with season filter."""
        mock_query = MagicMock()
        mock_query.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_query

        result = playoffs_service.get_playoff_bracket(season="2024")

        assert result["season"] == "2024"
        # Verify that both queries were executed (completed games and scheduled games)
        assert mock_db_session.execute.call_count == 2

    def test_mark_game_as_playoff(self, playoffs_service, mock_db_session):
        """Test marking a game as playoff game."""
        # Create mock game
        game = Mock(spec=Game, id=1, is_playoff_game=False)
        mock_db_session.get.return_value = game

        result = playoffs_service.mark_game_as_playoff(1)

        assert game.is_playoff_game is True
        mock_db_session.commit.assert_called_once()
        assert result == game

    def test_mark_game_as_playoff_not_found(self, playoffs_service, mock_db_session):
        """Test marking non-existent game as playoff."""
        mock_db_session.get.return_value = None

        with pytest.raises(ValueError, match="Game with ID 999 not found"):
            playoffs_service.mark_game_as_playoff(999)

    def test_unmark_game_as_playoff(self, playoffs_service, mock_db_session):
        """Test removing playoff designation from a game."""
        # Create mock game
        game = Mock(spec=Game, id=1, is_playoff_game=True)
        mock_db_session.get.return_value = game

        result = playoffs_service.unmark_game_as_playoff(1)

        assert game.is_playoff_game is False
        mock_db_session.commit.assert_called_once()
        assert result == game

    def test_unmark_game_as_playoff_not_found(self, playoffs_service, mock_db_session):
        """Test unmarking non-existent game as playoff."""
        mock_db_session.get.return_value = None

        with pytest.raises(ValueError, match="Game with ID 999 not found"):
            playoffs_service.unmark_game_as_playoff(999)

    def test_format_game_data(self, playoffs_service):
        """Test the _format_game_data method."""
        # Create mock game
        team1 = Mock(spec=Team)
        team1.id = 1
        team1.name = "Team A"
        team2 = Mock(spec=Team)
        team2.id = 2
        team2.name = "Team B"
        game = Mock(
            spec=Game,
            id=100,
            date=date(2025, 3, 15),
            playing_team_id=1,
            opponent_team_id=2,
            playing_team_score=95,
            opponent_team_score=90,
            playing_team=team1,
            opponent_team=team2,
        )

        result = playoffs_service._format_game_data(game)

        assert result["matchup"]["game_id"] == 100
        assert result["matchup"]["date"] == "2025-03-15"
        assert result["matchup"]["team1"]["team_id"] == 1
        assert result["matchup"]["team1"]["team_name"] == "Team A"
        assert result["matchup"]["team1"]["score"] == 95
        assert result["matchup"]["team2"]["team_id"] == 2
        assert result["matchup"]["team2"]["team_name"] == "Team B"
        assert result["matchup"]["team2"]["score"] == 90

    def test_get_playoff_bracket_no_champion_yet(self, playoffs_service, mock_db_session):
        """Test bracket when final game hasn't been played yet."""
        # Create mock teams and game
        team1 = Mock(spec=Team)
        team1.id = 1
        team1.name = "Team A"
        team2 = Mock(spec=Team)
        team2.id = 2
        team2.name = "Team B"

        final_game = Mock(
            spec=Game,
            id=101,
            date=date(2025, 3, 15),
            playing_team_id=1,
            opponent_team_id=2,
            playing_team_score=None,  # Game not played yet
            opponent_team_score=None,
            playing_team=team1,
            opponent_team=team2,
        )

        # Mock query results - first call returns completed games, second returns empty scheduled games
        completed_games_query = MagicMock()
        completed_games_query.scalars.return_value.all.return_value = [final_game]
        
        scheduled_games_query = MagicMock()
        scheduled_games_query.scalars.return_value.all.return_value = []
        
        mock_db_session.execute.side_effect = [completed_games_query, scheduled_games_query]

        result = playoffs_service.get_playoff_bracket()

        # Verify both queries were executed
        assert mock_db_session.execute.call_count == 2
        assert result["champion"] is None  # No champion yet
        assert result["finals"] is not None
        assert result["finals"]["matchup"]["team1"]["score"] is None
        assert result["finals"]["matchup"]["team2"]["score"] is None

    def test_get_playoff_bracket_with_scheduled_games(self, playoffs_service, mock_db_session):
        """Test getting bracket with scheduled playoff games."""
        # Create mock teams
        team1 = Mock(spec=Team)
        team1.id = 1
        team1.name = "Team A"
        team2 = Mock(spec=Team)
        team2.id = 2
        team2.name = "Team B"

        # Create mock scheduled game
        scheduled_game = Mock(
            spec=ScheduledGame,
            id=201,
            scheduled_date=date(2025, 3, 20),
            home_team_id=1,
            away_team_id=2,
            home_team=team1,
            away_team=team2,
        )

        # Mock query results - first call returns empty completed games, second returns scheduled games
        completed_games_query = MagicMock()
        completed_games_query.scalars.return_value.all.return_value = []
        
        scheduled_games_query = MagicMock()
        scheduled_games_query.scalars.return_value.all.return_value = [scheduled_game]
        
        mock_db_session.execute.side_effect = [completed_games_query, scheduled_games_query]

        result = playoffs_service.get_playoff_bracket()

        # Verify both queries were executed
        assert mock_db_session.execute.call_count == 2
        
        # Verify structure - now we always have 2 semi-finals slots, even if empty
        assert result["season"] == "2025"
        assert result["champion"] is None  # No champion for scheduled game
        assert result["finals"] is not None
        # With 1 game, it goes to finals, but we still have 2 TBD semi-finals slots
        assert len(result["semi_finals"]) == 2  # Now we ensure 2 slots always exist

        # Verify finals (scheduled game)
        finals = result["finals"]["matchup"]
        assert finals["game_id"] == "scheduled-201"
        assert finals["status"] == "scheduled"
        assert finals["team1"]["team_name"] == "Team A"
        assert finals["team1"]["score"] is None
        assert finals["team2"]["team_name"] == "Team B"
        assert finals["team2"]["score"] is None
        
        # Verify TBD semi-finals slots were added
        assert result["semi_finals"][0]["matchup"]["status"] == "tbd"
        assert result["semi_finals"][1]["matchup"]["status"] == "tbd"

    def test_determine_playoff_round_finals(self, playoffs_service, mock_db_session):
        """Test determining playoff round for finals game."""
        # Create mock teams
        team1 = Mock(spec=Team)
        team1.id = 1
        team1.name = "Team A"
        team2 = Mock(spec=Team)
        team2.id = 2
        team2.name = "Team B"

        # Create mock final game
        final_game = Mock(
            spec=Game,
            id=101,
            date=date(2025, 3, 15),
            playing_team_id=1,
            opponent_team_id=2,
            playing_team_score=100,
            opponent_team_score=95,
            playing_team=team1,
            opponent_team=team2,
        )

        # Mock query results
        completed_games_query = MagicMock()
        completed_games_query.scalars.return_value.all.return_value = [final_game]
        
        scheduled_games_query = MagicMock()
        scheduled_games_query.scalars.return_value.all.return_value = []
        
        # Mock both calls for determine_playoff_round (it calls get_playoff_bracket which makes 2 queries)
        mock_db_session.execute.side_effect = [completed_games_query, scheduled_games_query]

        result = playoffs_service.determine_playoff_round(101)
        assert result == "Finals"

    def test_determine_playoff_round_semi_finals(self, playoffs_service, mock_db_session):
        """Test determining playoff round for semi-finals game."""
        # Create mock teams
        team1 = Mock(spec=Team)
        team1.id = 1
        team1.name = "Team A"
        team2 = Mock(spec=Team)
        team2.id = 2
        team2.name = "Team B"
        team3 = Mock(spec=Team)
        team3.id = 3
        team3.name = "Team C"

        # Create mock games - finals + semi-finals
        final_game = Mock(
            spec=Game,
            id=101,
            date=date(2025, 3, 15),
            playing_team_id=1,
            opponent_team_id=2,
            playing_team_score=100,
            opponent_team_score=95,
            playing_team=team1,
            opponent_team=team2,
        )

        semi_game = Mock(
            spec=Game,
            id=102,
            date=date(2025, 3, 10),
            playing_team_id=1,
            opponent_team_id=3,
            playing_team_score=90,
            opponent_team_score=88,
            playing_team=team1,
            opponent_team=team3,
        )

        # Mock query results
        completed_games_query = MagicMock()
        completed_games_query.scalars.return_value.all.return_value = [final_game, semi_game]
        
        scheduled_games_query = MagicMock()
        scheduled_games_query.scalars.return_value.all.return_value = []
        
        # Mock both calls for determine_playoff_round (it calls get_playoff_bracket which makes 2 queries)
        mock_db_session.execute.side_effect = [completed_games_query, scheduled_games_query]

        result = playoffs_service.determine_playoff_round(102)
        assert result == "Semi-Finals"

    def test_determine_playoff_round_scheduled_game(self, playoffs_service, mock_db_session):
        """Test determining playoff round for scheduled game."""
        # Create mock teams
        team1 = Mock(spec=Team)
        team1.id = 1
        team1.name = "Team A"
        team2 = Mock(spec=Team)
        team2.id = 2
        team2.name = "Team B"

        # Create mock scheduled game
        scheduled_game = Mock(
            spec=ScheduledGame,
            id=201,
            scheduled_date=date(2025, 3, 20),
            home_team_id=1,
            away_team_id=2,
            home_team=team1,
            away_team=team2,
        )

        # Mock query results - empty completed games, scheduled game as finals
        completed_games_query = MagicMock()
        completed_games_query.scalars.return_value.all.return_value = []
        
        scheduled_games_query = MagicMock()
        scheduled_games_query.scalars.return_value.all.return_value = [scheduled_game]
        
        # Mock both calls for determine_playoff_round (it calls get_playoff_bracket which makes 2 queries)
        mock_db_session.execute.side_effect = [completed_games_query, scheduled_games_query]

        result = playoffs_service.determine_playoff_round("scheduled-201")
        assert result == "Finals"

    def test_determine_playoff_round_no_playoff_games(self, playoffs_service, mock_db_session):
        """Test determining playoff round when no playoff games exist."""
        # Mock empty query results
        completed_games_query = MagicMock()
        completed_games_query.scalars.return_value.all.return_value = []
        
        scheduled_games_query = MagicMock()
        scheduled_games_query.scalars.return_value.all.return_value = []
        
        # Mock both calls for determine_playoff_round (it calls get_playoff_bracket which makes 2 queries)
        mock_db_session.execute.side_effect = [completed_games_query, scheduled_games_query]

        result = playoffs_service.determine_playoff_round(999)
        assert result is None

    def test_determine_playoff_round_same_day_semi_finals(self, playoffs_service, mock_db_session):
        """Test determining playoff round for games on same day - should both be semi-finals."""
        # Create mock teams
        team1 = Mock(spec=Team)
        team1.id = 1
        team1.name = "Team A"
        team2 = Mock(spec=Team)
        team2.id = 2
        team2.name = "Team B"
        team3 = Mock(spec=Team)
        team3.id = 3
        team3.name = "Team C"
        team4 = Mock(spec=Team)
        team4.id = 4
        team4.name = "Team D"

        # Create two scheduled games on the same date
        scheduled_game1 = Mock(
            spec=ScheduledGame,
            id=201,
            scheduled_date=date(2025, 3, 20),
            home_team_id=1,
            away_team_id=2,
            home_team=team1,
            away_team=team2,
        )

        scheduled_game2 = Mock(
            spec=ScheduledGame,
            id=202,
            scheduled_date=date(2025, 3, 20),  # Same date
            home_team_id=3,
            away_team_id=4,
            home_team=team3,
            away_team=team4,
        )

        # Mock query results - empty completed games, two scheduled games on same date
        completed_games_query = MagicMock()
        completed_games_query.scalars.return_value.all.return_value = []
        
        scheduled_games_query = MagicMock()
        scheduled_games_query.scalars.return_value.all.return_value = [scheduled_game1, scheduled_game2]
        
        # Mock both calls for determine_playoff_round (it calls get_playoff_bracket which makes 2 queries)
        mock_db_session.execute.side_effect = [completed_games_query, scheduled_games_query]

        # Both games should be semi-finals, not one finals and one semi-finals
        result1 = playoffs_service.determine_playoff_round("scheduled-201")
        
        # Reset side effect for second call
        mock_db_session.execute.side_effect = [completed_games_query, scheduled_games_query]
        result2 = playoffs_service.determine_playoff_round("scheduled-202")
        
        assert result1 == "Semi-Finals"
        assert result2 == "Semi-Finals"
