# tests/unit/services/test_awards_service.py

from datetime import date
from unittest.mock import Mock, patch

import pytest

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


class TestCalculateDubClub:
    """Test Dub Club award calculation."""

    @patch("app.services.awards_service.crud_game.get_all_games")
    @patch("app.services.awards_service.create_player_award_safe")
    @patch("app.services.awards_service.get_awards_by_week")
    def test_calculate_dub_club_basic(self, mock_get_awards, mock_create_award, mock_get_games):
        """Test basic Dub Club calculation - players scoring 20+ points."""
        session = Mock()

        # Create mock games with stats
        game1 = Mock()
        game1.date = date(2024, 1, 15)  # Monday
        game1.id = 1

        # Player 1 scores 25 points (10 2PM + 1 3PM + 2 FTM = 25)
        stat1 = Mock()
        stat1.player_id = 1
        stat1.total_2pm = 10
        stat1.total_3pm = 1
        stat1.total_ftm = 2
        stat1.game_id = 1

        # Player 2 scores exactly 20 points (8 2PM + 0 3PM + 4 FTM = 20)
        stat2 = Mock()
        stat2.player_id = 2
        stat2.total_2pm = 8
        stat2.total_3pm = 0
        stat2.total_ftm = 4
        stat2.game_id = 1

        # Player 3 scores 19 points (should not get award)
        stat3 = Mock()
        stat3.player_id = 3
        stat3.total_2pm = 7
        stat3.total_3pm = 1
        stat3.total_ftm = 2
        stat3.game_id = 1

        game1.player_game_stats = [stat1, stat2, stat3]
        mock_get_games.return_value = [game1]

        # Mock awards created
        mock_award1 = Mock()
        mock_award2 = Mock()
        mock_create_award.side_effect = [mock_award1, mock_award2]
        mock_get_awards.return_value = [mock_award1, mock_award2]

        from app.services.awards_service import calculate_dub_club

        results = calculate_dub_club(session, season=None, recalculate=False)

        # Should create awards for players 1 and 2
        assert mock_create_award.call_count == 2

        # Check first award call (player 1 with 25 points)
        call1_args = mock_create_award.call_args_list[0]
        assert call1_args.kwargs["player_id"] == 1
        assert call1_args.kwargs["points_scored"] == 25
        assert call1_args.kwargs["award_type"] == "dub_club"

        # Check second award call (player 2 with 20 points)
        call2_args = mock_create_award.call_args_list[1]
        assert call2_args.kwargs["player_id"] == 2
        assert call2_args.kwargs["points_scored"] == 20

        assert results == {"2024": 2}

    @patch("app.services.awards_service.crud_game.get_all_games")
    @patch("app.services.awards_service.create_player_award_safe")
    @patch("app.services.awards_service.get_awards_by_week")
    def test_dub_club_multiple_games_same_week(self, mock_get_awards, mock_create_award, mock_get_games):
        """Test Dub Club when player scores 20+ in multiple games same week."""
        session = Mock()

        # Two games in same week
        game1 = Mock()
        game1.date = date(2024, 1, 15)  # Monday
        game1.id = 1

        game2 = Mock()
        game2.date = date(2024, 1, 17)  # Wednesday
        game2.id = 2

        # Player 1 scores 22 points in game 1
        stat1 = Mock()
        stat1.player_id = 1
        stat1.total_2pm = 10
        stat1.total_3pm = 0
        stat1.total_ftm = 2
        stat1.game_id = 1

        # Player 1 scores 30 points in game 2 (higher score)
        stat2 = Mock()
        stat2.player_id = 1
        stat2.total_2pm = 12
        stat2.total_3pm = 2
        stat2.total_ftm = 0
        stat2.game_id = 2

        game1.player_game_stats = [stat1]
        game2.player_game_stats = [stat2]
        mock_get_games.return_value = [game1, game2]

        mock_award = Mock()
        mock_create_award.return_value = mock_award
        mock_get_awards.return_value = [mock_award]

        from app.services.awards_service import calculate_dub_club

        results = calculate_dub_club(session, season=None, recalculate=False)

        # Should create two awards - one for each qualifying game (20+ points)
        assert mock_create_award.call_count == 2

        # Verify both awards are for the same player
        all_calls = mock_create_award.call_args_list
        assert all_calls[0].kwargs["player_id"] == 1
        assert all_calls[1].kwargs["player_id"] == 1

        # Verify correct points for each game
        points_awarded = {call.kwargs["points_scored"] for call in all_calls}
        assert points_awarded == {22, 30}  # Both qualifying scores

        # Verify correct game_ids are passed
        game_ids_awarded = {call.kwargs["game_id"] for call in all_calls}
        assert game_ids_awarded == {1, 2}  # Both games

        assert results == {"2024": 1}  # Still reports as 1 week with awards

    @patch("app.services.awards_service.crud_game.get_all_games")
    @patch("app.services.awards_service.delete_all_awards_by_type")
    def test_dub_club_recalculate(self, mock_delete, mock_get_games):
        """Test Dub Club recalculation deletes existing awards."""
        session = Mock()
        mock_get_games.return_value = []
        mock_delete.return_value = 3

        from app.services.awards_service import calculate_dub_club

        calculate_dub_club(session, season=None, recalculate=True)

        mock_delete.assert_called_once_with(session, "dub_club")
        session.commit.assert_called()


class TestCalculateMarksmanAward:
    """Test Marksman Award calculation."""

    @patch("app.services.awards_service.crud_game.get_all_games")
    @patch("app.services.awards_service.create_player_award_safe")
    @patch("app.services.awards_service.get_awards_by_week")
    def test_calculate_marksman_award_basic(self, mock_get_awards, mock_create_award, mock_get_games):
        """Test basic Marksman Award calculation - most efficient shooter with 4-8 FGA."""
        session = Mock()

        # Create mock games with stats
        game1 = Mock()
        game1.date = date(2024, 1, 15)  # Monday
        game1.id = 1

        # Player 1: 5 FGA, 4 made = 80% (qualifies, high %)
        stat1 = Mock()
        stat1.player_id = 1
        stat1.total_2pm = 2
        stat1.total_3pm = 2
        stat1.total_2pa = 3
        stat1.total_3pa = 2
        # FGA = 5, FGM = 4, FG% = 80%

        # Player 2: 6 FGA, 3 made = 50% (qualifies, lower %)
        stat2 = Mock()
        stat2.player_id = 2
        stat2.total_2pm = 1
        stat2.total_3pm = 2
        stat2.total_2pa = 2
        stat2.total_3pa = 4
        # FGA = 6, FGM = 3, FG% = 50%

        # Player 3: 3 FGA (doesn't qualify - too few attempts)
        stat3 = Mock()
        stat3.player_id = 3
        stat3.total_2pm = 3
        stat3.total_3pm = 0
        stat3.total_2pa = 3
        stat3.total_3pa = 0
        # FGA = 3, doesn't qualify

        # Player 4: 8 FGA, 8 made = 100% (qualifies and should win)
        stat4 = Mock()
        stat4.player_id = 4
        stat4.total_2pm = 6
        stat4.total_3pm = 2
        stat4.total_2pa = 6
        stat4.total_3pa = 2
        # FGA = 8, FGM = 8, FG% = 100%

        game1.player_game_stats = [stat1, stat2, stat3, stat4]
        mock_get_games.return_value = [game1]

        mock_award = Mock()
        mock_create_award.return_value = mock_award
        mock_get_awards.return_value = [mock_award]

        from app.services.awards_service import calculate_marksman_award

        results = calculate_marksman_award(session, season=None, recalculate=False)

        # Should create award for player 4 only (highest FG% among qualifiers: 100% vs 80% vs 50%)
        assert mock_create_award.call_count == 1
        assert mock_create_award.call_args.kwargs["player_id"] == 4
        assert mock_create_award.call_args.kwargs["award_type"] == "marksman_award"
        assert results == {"2024": 1}


class TestCalculatePerfectPerformance:
    """Test Perfect Performance Award calculation."""

    @patch("app.services.awards_service.crud_game.get_all_games")
    @patch("app.services.awards_service.create_player_award_safe")
    @patch("app.services.awards_service.get_awards_by_week")
    def test_calculate_perfect_performance_basic(self, mock_get_awards, mock_create_award, mock_get_games):
        """Test basic Perfect Performance Award calculation - 100% shooting with 3+ makes."""
        session = Mock()

        # Create mock games with stats
        game1 = Mock()
        game1.date = date(2024, 1, 15)  # Monday
        game1.id = 1

        # Player 1: Perfect game with 5 makes (qualifies)
        stat1 = Mock()
        stat1.player_id = 1
        stat1.total_2pm = 2
        stat1.total_3pm = 1
        stat1.total_ftm = 2
        stat1.total_2pa = 2  # Perfect 2pt
        stat1.total_3pa = 1  # Perfect 3pt
        stat1.total_fta = 2  # Perfect FT
        # Total makes = 5, all perfect

        # Player 2: Only 2 makes (doesn't qualify - too few makes)
        stat2 = Mock()
        stat2.player_id = 2
        stat2.total_2pm = 1
        stat2.total_3pm = 0
        stat2.total_ftm = 1
        stat2.total_2pa = 1
        stat2.total_3pa = 0
        stat2.total_fta = 1
        # Total makes = 2, doesn't qualify

        # Player 3: 4 makes but missed a shot (doesn't qualify - not perfect)
        stat3 = Mock()
        stat3.player_id = 3
        stat3.total_2pm = 2
        stat3.total_3pm = 1
        stat3.total_ftm = 1
        stat3.total_2pa = 3  # Missed one 2pt
        stat3.total_3pa = 1
        stat3.total_fta = 1
        # Total makes = 4, but not perfect

        game1.player_game_stats = [stat1, stat2, stat3]
        mock_get_games.return_value = [game1]

        mock_award = Mock()
        mock_create_award.return_value = mock_award
        mock_get_awards.return_value = [mock_award]

        from app.services.awards_service import calculate_perfect_performance

        results = calculate_perfect_performance(session, season=None, recalculate=False)

        # Should create award for player 1 only (perfect with 3+ makes)
        assert mock_create_award.call_count == 1
        assert mock_create_award.call_args.kwargs["player_id"] == 1
        assert mock_create_award.call_args.kwargs["award_type"] == "perfect_performance"
        assert results == {"2024": 1}

    @patch("app.services.awards_service.crud_game.get_all_games")
    @patch("app.services.awards_service.create_player_award_safe")
    @patch("app.services.awards_service.get_awards_by_week")
    def test_perfect_performance_multiple_winners(self, mock_get_awards, mock_create_award, mock_get_games):
        """Test Perfect Performance Award with multiple winners in same week."""
        session = Mock()

        # Create mock games with stats
        game1 = Mock()
        game1.date = date(2024, 1, 15)  # Monday
        game1.id = 1

        # Player 1: Perfect game with 3 makes
        stat1 = Mock()
        stat1.player_id = 1
        stat1.total_2pm = 1
        stat1.total_3pm = 1
        stat1.total_ftm = 1
        stat1.total_2pa = 1
        stat1.total_3pa = 1
        stat1.total_fta = 1

        # Player 2: Perfect game with 4 makes
        stat2 = Mock()
        stat2.player_id = 2
        stat2.total_2pm = 2
        stat2.total_3pm = 1
        stat2.total_ftm = 1
        stat2.total_2pa = 2
        stat2.total_3pa = 1
        stat2.total_fta = 1

        game1.player_game_stats = [stat1, stat2]
        mock_get_games.return_value = [game1]

        mock_award1 = Mock()
        mock_award2 = Mock()
        mock_create_award.side_effect = [mock_award1, mock_award2]
        mock_get_awards.return_value = [mock_award1, mock_award2]

        from app.services.awards_service import calculate_perfect_performance

        results = calculate_perfect_performance(session, season=None, recalculate=False)

        # Both players should win
        assert mock_create_award.call_count == 2
        assert results == {"2024": 2}


class TestCalculateBreakoutPerformance:
    """Test Breakout Performance Award calculation."""

    @patch("app.services.awards_service.crud_game.get_all_games")
    @patch("app.services.awards_service.create_player_award_safe")
    @patch("app.services.awards_service.get_awards_by_week")
    @pytest.mark.skip(reason="Complex database query mocking - covered by integration tests")
    def test_calculate_breakout_performance_basic(self, mock_get_awards, mock_create_award, mock_get_games):
        """Test basic Breakout Performance Award calculation."""
        session = Mock()

        # Create mock current week game
        current_game = Mock()
        current_game.date = date(2024, 1, 15)  # Week we're calculating
        current_game.id = 4

        # Player 1 stats for current game: 24 points
        current_stat = Mock()
        current_stat.player_id = 1
        current_stat.total_2pm = 9
        current_stat.total_3pm = 2
        current_stat.total_ftm = 0
        # 24 points total

        current_game.player_game_stats = [current_stat]

        # Create mock historical games for season average calculation
        hist_game1 = Mock()
        hist_game1.date = date(2024, 1, 1)
        hist_game1.id = 1
        hist_stat1 = Mock()
        hist_stat1.player_id = 1
        hist_stat1.total_2pm = 3
        hist_stat1.total_3pm = 1
        hist_stat1.total_ftm = 2
        # 8 points
        hist_game1.player_game_stats = [hist_stat1]

        hist_game2 = Mock()
        hist_game2.date = date(2024, 1, 8)
        hist_game2.id = 2
        hist_stat2 = Mock()
        hist_stat2.player_id = 1
        hist_stat2.total_2pm = 4
        hist_stat2.total_3pm = 0
        hist_stat2.total_ftm = 4
        # 12 points
        hist_game2.player_game_stats = [hist_stat2]

        hist_game3 = Mock()
        hist_game3.date = date(2024, 1, 10)
        hist_game3.id = 3
        hist_stat3 = Mock()
        hist_stat3.player_id = 1
        hist_stat3.total_2pm = 2
        hist_stat3.total_3pm = 2
        hist_stat3.total_ftm = 0
        # 10 points
        hist_game3.player_game_stats = [hist_stat3]

        # Mock database query to return historical games
        mock_get_games.return_value = [current_game]

        # Mock session query for historical games
        session.query.return_value.join.return_value.filter.return_value.all.return_value = [
            hist_game1,
            hist_game2,
            hist_game3,
            current_game,
        ]

        mock_award = Mock()
        mock_create_award.return_value = mock_award
        mock_get_awards.return_value = [mock_award]

        from app.services.awards_service import calculate_breakout_performance

        results = calculate_breakout_performance(session, season=None, recalculate=False)

        # Player had 3 prior games with avg = (8+12+10)/3 = 10 points
        # Current game = 24 points
        # Improvement = (24-10)/10 = 140% improvement
        # Should qualify and win award
        assert mock_create_award.call_count == 1
        assert mock_create_award.call_args.kwargs["player_id"] == 1
        assert mock_create_award.call_args.kwargs["award_type"] == "breakout_performance"
        assert mock_create_award.call_args.kwargs["points_scored"] == 24
        assert results == {"2024": 1}
