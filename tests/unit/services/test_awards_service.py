# tests/unit/services/test_awards_service.py

from datetime import date
from unittest.mock import Mock, patch

from app.services.awards_service import (
    calculate_player_of_the_week,
    get_current_season,
    get_player_potw_summary,
    get_season_from_date,
)


class TestSeasonHelpers:
    """Test season utility functions."""

    def test_get_season_from_date(self):
        """Test season calculation from date."""
        assert get_season_from_date(date(2024, 1, 15)) == "2024"
        assert get_season_from_date(date(2024, 6, 30)) == "2024"
        assert get_season_from_date(date(2024, 12, 31)) == "2024"
        assert get_season_from_date(date(2025, 1, 1)) == "2025"

    @patch("app.services.awards_service.date")
    def test_get_current_season(self, mock_date):
        """Test current season calculation."""
        mock_date.today.return_value = date(2024, 7, 15)
        assert get_current_season() == "2024"


class TestCalculatePlayerOfTheWeek:
    """Test main POTW calculation function."""

    @patch("app.services.awards_service.crud_game.get_all_games")
    @patch("app.services.awards_service._calculate_week_winners")
    @patch("app.services.awards_service.get_awards_by_week")
    def test_calculate_all_seasons(self, mock_get_awards, mock_week_winners, mock_get_games):
        """Test calculating awards for all seasons."""
        session = Mock()

        # Mock games from different seasons
        game1 = Mock()
        game1.date = date(2024, 1, 15)  # Monday

        game2 = Mock()
        game2.date = date(2024, 1, 22)  # Following Monday (different week)

        game3 = Mock()
        game3.date = date(2025, 2, 10)  # Different season

        mock_get_games.return_value = [game1, game2, game3]
        # Mock get_awards_by_week to return the awards for counting
        # Each call corresponds to a week being processed
        mock_awards_week1 = [Mock(), Mock()]  # 2 awards for week 1 of 2024
        mock_awards_week2 = []  # 0 awards for week 2 of 2024
        mock_awards_week3 = [Mock()]  # 1 award for week 1 of 2025
        mock_get_awards.side_effect = [mock_awards_week1, mock_awards_week2, mock_awards_week3]

        # _calculate_week_winners returns list of player IDs (not used in counting)
        mock_week_winners.side_effect = [[1, 2], [], [3]]  # Player IDs for each week

        results = calculate_player_of_the_week(session, season=None, recalculate=False)

        # Should process 3 weeks across 2 seasons
        assert mock_week_winners.call_count == 3
        assert results == {"2024": 2, "2025": 1}

    @patch("app.services.awards_service.crud_game.get_all_games")
    @patch("app.services.awards_service._calculate_week_winners")
    @patch("app.services.awards_service.get_awards_by_week")
    def test_calculate_specific_season(self, mock_get_awards, mock_week_winners, mock_get_games):
        """Test calculating awards for specific season."""
        session = Mock()

        # Mock games from different seasons
        game1 = Mock()
        game1.date = date(2024, 1, 15)

        game2 = Mock()
        game2.date = date(2025, 1, 15)  # Different season - should be filtered out

        mock_get_games.return_value = [game1, game2]
        # Mock get_awards_by_week to return 1 award for the single 2024 week
        mock_get_awards.return_value = [Mock()]  # 1 award in the database
        mock_week_winners.return_value = [1]  # Player ID who won

        results = calculate_player_of_the_week(session, season="2024", recalculate=False)

        # Should only process 2024 game
        assert mock_week_winners.call_count == 1
        assert results == {"2024": 1}

    @patch("app.services.awards_service.crud_game.get_all_games")
    @patch("app.services.awards_service.delete_all_awards_by_type")
    def test_calculate_with_recalculate(self, mock_delete, mock_get_games):
        """Test recalculate flag resets awards."""
        session = Mock()
        mock_get_games.return_value = []
        mock_delete.return_value = 5

        calculate_player_of_the_week(session, season=None, recalculate=True)

        # Should delete existing awards
        mock_delete.assert_called_once_with(session, "player_of_the_week")

    @patch("app.services.awards_service.crud_game.get_all_games")
    def test_calculate_no_games(self, mock_get_games):
        """Test calculation with no games."""
        session = Mock()
        mock_get_games.return_value = []

        results = calculate_player_of_the_week(session, season=None, recalculate=False)

        assert results == {}

    @patch("app.services.awards_service.crud_game.get_all_games")
    @patch("app.services.awards_service._calculate_week_winners")
    @patch("app.services.awards_service.get_awards_by_week")
    def test_week_grouping(self, mock_get_awards, mock_week_winners, mock_get_games):
        """Test that games are properly grouped by week."""
        session = Mock()

        # Games on same week (Monday-Sunday)
        monday = date(2024, 1, 15)  # Monday
        tuesday = date(2024, 1, 16)  # Tuesday (same week)
        sunday = date(2024, 1, 21)  # Sunday (same week)
        next_monday = date(2024, 1, 22)  # Monday (next week)

        game1 = Mock()
        game1.date = monday

        game2 = Mock()
        game2.date = tuesday

        game3 = Mock()
        game3.date = sunday

        game4 = Mock()
        game4.date = next_monday

        mock_get_games.return_value = [game1, game2, game3, game4]
        mock_get_awards.return_value = []  # No existing awards
        mock_week_winners.return_value = [1]

        calculate_player_of_the_week(session, season=None, recalculate=False)

        # Should be called twice - once for each week
        assert mock_week_winners.call_count == 2

        # Check that first three games are grouped together
        first_call_games = mock_week_winners.call_args_list[0][0][1]
        assert len(first_call_games) == 3

        # Check that last game is in separate week
        second_call_games = mock_week_winners.call_args_list[1][0][1]
        assert len(second_call_games) == 1


class TestGetPlayerPotwSummary:
    """Test getting comprehensive POTW summary."""

    def test_get_player_potw_summary_with_awards(self, unit_db_session, shared_test_player):
        """Test getting summary for player with awards."""
        with (
            patch("app.services.awards_service.get_current_season") as mock_current,
            patch("app.services.awards_service.get_player_award_counts_by_season") as mock_counts,
            patch("app.services.awards_service.get_player_awards_by_type") as mock_recent,
        ):
            mock_current.return_value = "2024"
            mock_counts.return_value = {"2024": 2, "2023": 1}

            # Mock recent awards
            mock_award = Mock()
            mock_award.season = "2024"
            mock_award.week_date = date(2024, 1, 1)
            mock_award.points_scored = 30
            mock_award.created_at = date(2024, 1, 2)
            mock_recent.return_value = [mock_award]

            summary = get_player_potw_summary(unit_db_session, shared_test_player.id)

            assert summary["current_season_count"] == 2
            assert summary["total_count"] == 3
            assert summary["awards_by_season"] == {"2024": 2, "2023": 1}
            assert len(summary["recent_awards"]) == 1
            assert summary["recent_awards"][0]["season"] == "2024"
            assert summary["recent_awards"][0]["points_scored"] == 30

    def test_get_player_potw_summary_no_awards(self, unit_db_session, shared_test_player):
        """Test getting summary for player with no awards."""
        with (
            patch("app.services.awards_service.get_current_season") as mock_current,
            patch("app.services.awards_service.get_player_award_counts_by_season") as mock_counts,
            patch("app.services.awards_service.get_player_awards_by_type") as mock_recent,
        ):
            mock_current.return_value = "2024"
            mock_counts.return_value = {}
            mock_recent.return_value = []

            summary = get_player_potw_summary(unit_db_session, shared_test_player.id)

            assert summary["current_season_count"] == 0
            assert summary["total_count"] == 0
            assert summary["awards_by_season"] == {}
            assert summary["recent_awards"] == []


class TestWeekCalculation:
    """Test week-based calculation logic."""

    def test_week_grouping_integration(self, unit_db_session):
        """Test that games are properly grouped by week in integration."""
        test_data = create_test_data(unit_db_session)

        # Create games on different days of the same week
        game1 = test_data["game1"]  # Monday
        game1.date = date(2024, 1, 1)  # Monday

        game2 = test_data["game2"]  # Same week (Sunday)
        game2.date = date(2024, 1, 7)  # Sunday

        with patch("app.services.awards_service.crud_game.get_all_games") as mock_get_games:
            mock_get_games.return_value = [game1, game2]

            results = calculate_player_of_the_week(unit_db_session)

            # Should give only 1 award since both games are in same week
            assert sum(results.values()) == 1

    def test_different_weeks_integration(self, unit_db_session):
        """Test games in different weeks get separate awards."""
        test_data = create_test_data(unit_db_session)

        # Create games in different weeks
        game1 = test_data["game1"]
        game1.date = date(2024, 1, 1)  # Week 1

        game2 = test_data["game2"]
        game2.date = date(2024, 1, 8)  # Week 2 (Monday of next week)

        with patch("app.services.awards_service.crud_game.get_all_games") as mock_get_games:
            mock_get_games.return_value = [game1, game2]

            results = calculate_player_of_the_week(unit_db_session)

            # Should give 2 awards since games are in different weeks
            assert sum(results.values()) == 2


def create_test_data(session):
    """Create test data for awards service tests."""
    from app.data_access.models import Game, Player, PlayerGameStats, Team

    # Create teams
    team1 = Team(name="Team A")
    team2 = Team(name="Team B")
    session.add_all([team1, team2])
    session.flush()

    # Create players
    player1 = Player(name="Player 1", team_id=team1.id, jersey_number="1")
    player2 = Player(name="Player 2", team_id=team1.id, jersey_number="2")
    session.add_all([player1, player2])
    session.flush()

    # Create games
    game1 = Game(
        date=date(2024, 1, 1),
        playing_team_id=team1.id,
        opponent_team_id=team2.id,
        playing_team_score=100,
        opponent_team_score=90,
    )
    game2 = Game(
        date=date(2024, 1, 8),
        playing_team_id=team1.id,
        opponent_team_id=team2.id,
        playing_team_score=110,
        opponent_team_score=95,
    )
    game3 = Game(
        date=date(2025, 1, 1),
        playing_team_id=team1.id,
        opponent_team_id=team2.id,
        playing_team_score=105,
        opponent_team_score=88,
    )
    session.add_all([game1, game2, game3])
    session.flush()

    # Create player stats
    stats1 = PlayerGameStats(game_id=game1.id, player_id=player1.id, total_2pm=5, total_3pm=2, total_ftm=3)
    stats2 = PlayerGameStats(game_id=game1.id, player_id=player2.id, total_2pm=3, total_3pm=1, total_ftm=2)
    stats3 = PlayerGameStats(game_id=game2.id, player_id=player1.id, total_2pm=6, total_3pm=1, total_ftm=4)
    stats4 = PlayerGameStats(game_id=game3.id, player_id=player2.id, total_2pm=4, total_3pm=3, total_ftm=2)
    session.add_all([stats1, stats2, stats3, stats4])
    session.flush()

    return {
        "team1": team1,
        "team2": team2,
        "player1": player1,
        "player2": player2,
        "game1": game1,
        "game2": game2,
        "game3": game3,
        "stats1": stats1,
        "stats2": stats2,
        "stats3": stats3,
        "stats4": stats4,
    }
