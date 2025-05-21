"""
Test module for the ReportGenerator.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.data_access.models import Game, Player, PlayerGameStats, Team
from app.reports.report_generator import ReportGenerator


class TestReportGenerator:
    """Tests for the ReportGenerator."""

    @pytest.fixture
    def mock_game_data(self):
        """Create mock game data for testing reports."""
        team_a = Team(id=1, name="Team A")
        team_b = Team(id=2, name="Team B")

        game = Game(
            id=1, date="2025-05-01", playing_team_id=1, opponent_team_id=2, playing_team=team_a, opponent_team=team_b
        )

        player_a1 = Player(id=1, name="Player One", jersey_number=10, team_id=1, team=team_a)
        player_a2 = Player(id=2, name="Player Two", jersey_number=23, team_id=1, team=team_a)
        player_b1 = Player(id=3, name="Player Alpha", jersey_number=5, team_id=2, team=team_b)
        player_b2 = Player(id=4, name="Player Beta", jersey_number=15, team_id=2, team=team_b)

        player_game_stats = [
            # Team A players
            PlayerGameStats(
                id=1,
                game_id=1,
                player_id=1,
                fouls=2,
                total_ftm=3,
                total_fta=4,
                total_2pm=5,
                total_2pa=8,
                total_3pm=2,
                total_3pa=5,
                player=player_a1,
                game=game,
            ),
            PlayerGameStats(
                id=2,
                game_id=1,
                player_id=2,
                fouls=3,
                total_ftm=1,
                total_fta=2,
                total_2pm=4,
                total_2pa=6,
                total_3pm=1,
                total_3pa=3,
                player=player_a2,
                game=game,
            ),
            # Team B players
            PlayerGameStats(
                id=3,
                game_id=1,
                player_id=3,
                fouls=1,
                total_ftm=0,
                total_fta=2,
                total_2pm=6,
                total_2pa=10,
                total_3pm=3,
                total_3pa=7,
                player=player_b1,
                game=game,
            ),
            PlayerGameStats(
                id=4,
                game_id=1,
                player_id=4,
                fouls=4,
                total_ftm=4,
                total_fta=4,
                total_2pm=3,
                total_2pa=5,
                total_3pm=0,
                total_3pa=2,
                player=player_b2,
                game=game,
            ),
        ]

        return {
            "game": game,
            "player_game_stats": player_game_stats,
            "teams": [team_a, team_b],
            "players": [player_a1, player_a2, player_b1, player_b2],
        }

    @pytest.fixture
    def mock_quarter_stats(self):
        """Mock quarter stats data."""
        # Create quarter stats matching the overall game stats
        return [
            # For player 1
            MagicMock(id=1, player_game_stats_id=1, quarter=1, ftm=1, fta=2, fg2m=2, fg2a=4, fg3m=1, fg3a=2),
            MagicMock(id=2, player_game_stats_id=1, quarter=2, ftm=2, fta=2, fg2m=3, fg2a=4, fg3m=1, fg3a=3),
            # For player 2 (similar pattern)
            MagicMock(id=3, player_game_stats_id=2, quarter=1, ftm=0, fta=1, fg2m=2, fg2a=3, fg3m=0, fg3a=1),
            MagicMock(id=4, player_game_stats_id=2, quarter=2, ftm=1, fta=1, fg2m=2, fg2a=3, fg3m=1, fg3a=2),
        ]

    @pytest.fixture
    def mock_crud_modules(self, mock_game_data, mock_quarter_stats):
        """Mock the CRUD modules used by ReportGenerator."""
        # Mock each CRUD module
        mocked_crud_game = MagicMock()
        mocked_crud_team = MagicMock()
        mocked_crud_player = MagicMock()
        mocked_crud_player_game_stats = MagicMock()
        mocked_crud_player_quarter_stats = MagicMock()

        # Set up return values
        mocked_crud_game.get_game_by_id.side_effect = lambda session, game_id: (
            mock_game_data["game"] if game_id == 1 else None
        )

        mocked_crud_team.get_team_by_id.side_effect = lambda session, team_id: (
            mock_game_data["teams"][0] if team_id == 1 else mock_game_data["teams"][1] if team_id == 2 else None
        )

        mocked_crud_player.get_player_by_id.side_effect = lambda session, player_id: (
            next((p for p in mock_game_data["players"] if p.id == player_id), None)
        )

        mocked_crud_player_game_stats.get_player_game_stats_by_game.side_effect = lambda session, game_id: (
            mock_game_data["player_game_stats"] if game_id == 1 else []
        )

        mocked_crud_player_quarter_stats.get_player_quarter_stats.side_effect = lambda session, pgs_id: (
            [qs for qs in mock_quarter_stats if qs.player_game_stats_id == pgs_id]
        )

        return {
            "crud_game": mocked_crud_game,
            "crud_team": mocked_crud_team,
            "crud_player": mocked_crud_player,
            "crud_player_game_stats": mocked_crud_player_game_stats,
            "crud_player_quarter_stats": mocked_crud_player_quarter_stats,
        }

    @pytest.fixture
    def mock_stats_calculator(self):
        """Create a mock stats calculator module."""
        mock_module = MagicMock()

        # Mock the calculation functions
        mock_module.calculate_percentage.side_effect = lambda makes, attempts: makes / attempts if attempts else None

        mock_module.calculate_points.side_effect = lambda ftm, fg2m, fg3m: ftm + 2 * fg2m + 3 * fg3m

        mock_module.calculate_efg.side_effect = lambda total_fgm, fg3m, total_fga: (
            (total_fgm + 0.5 * fg3m) / total_fga if total_fga else None
        )

        mock_module.calculate_ts.side_effect = lambda points, total_fga, fta: (
            points / (2 * (total_fga + 0.44 * fta)) if (total_fga + fta) else None
        )

        return mock_module

    def test_init(self, db_session, mock_stats_calculator):
        """Test initializing the report generator."""
        report_generator = ReportGenerator(db_session, mock_stats_calculator)
        assert report_generator.db_session == db_session
        assert report_generator.stats_calculator == mock_stats_calculator

    @patch("app.reports.report_generator.crud_game")
    @patch("app.reports.report_generator.crud_team")
    @patch("app.reports.report_generator.crud_player")
    @patch("app.reports.report_generator.crud_player_game_stats")
    @patch("app.reports.report_generator.crud_player_quarter_stats")
    def test_get_game_box_score_data(
        self,
        mock_crud_pqs,
        mock_crud_pgs,
        mock_crud_player,
        mock_crud_team,
        mock_crud_game,
        db_session,
        mock_stats_calculator,
        mock_game_data,
        mock_quarter_stats,
    ):
        """Test getting game box score data."""
        # Set up the CRUD mocks
        mock_crud_game.get_game_by_id.return_value = mock_game_data["game"]
        mock_crud_team.get_team_by_id.side_effect = lambda session, team_id: (
            mock_game_data["teams"][0] if team_id == 1 else mock_game_data["teams"][1] if team_id == 2 else None
        )
        mock_crud_player.get_player_by_id.side_effect = lambda session, player_id: (
            next((p for p in mock_game_data["players"] if p.id == player_id), None)
        )
        mock_crud_pgs.get_player_game_stats_by_game.return_value = mock_game_data["player_game_stats"]
        # Provide MagicMock objects for all four quarters for each player_game_stats
        def mock_get_quarter_stats(session, pgs_id):
            return [
                MagicMock(player_game_stats_id=pgs_id, quarter=q, ftm=1, fta=2, fg2m=2, fg2a=4, fg3m=1, fg3a=2)
                for q in range(1, 5)
            ]
        mock_crud_pqs.get_player_quarter_stats.side_effect = mock_get_quarter_stats

        report_generator = ReportGenerator(db_session, mock_stats_calculator)

        player_stats, game_info = report_generator.get_game_box_score_data(1)

        # Check game info
        assert game_info["date"] == "2025-05-01"
        assert game_info["playing_team"] == "Team A"
        assert game_info["opponent_team"] == "Team B"

        # Check player stats were calculated (checking first player)
        assert len(player_stats) > 0

        # Verify the CRUD calls were made correctly
        mock_crud_game.get_game_by_id.assert_called_once_with(db_session, 1)
        mock_crud_pgs.get_player_game_stats_by_game.assert_called_once_with(db_session, 1)

    @patch("app.reports.report_generator.crud_game")
    def test_get_game_box_score_data_not_found(self, mock_crud_game, db_session, mock_stats_calculator):
        """Test getting game box score data for a non-existent game."""
        # Setup mock to return None for non-existent game
        mock_crud_game.get_game_by_id.return_value = None

        report_generator = ReportGenerator(db_session, mock_stats_calculator)

        # Try to get data for non-existent game
        with pytest.raises(ValueError) as excinfo:
            report_generator.get_game_box_score_data(999)

        assert "Game not found" in str(excinfo.value)
        mock_crud_game.get_game_by_id.assert_called_once_with(db_session, 999)

    def test_player_box_score_with_new_stats(
        self, db_session, mock_stats_calculator, mock_game_data, mock_quarter_stats
    ):
        """Test that player box scores include PPSA and scoring distribution."""
        # Set up mocks for _calculate_player_box_score
        player = mock_game_data["players"][0]
        pgs = mock_game_data["player_game_stats"][0]
        playing_team = mock_game_data["teams"][0]
        opponent_team = mock_game_data["teams"][1]

        # Add mocks for the new statistics methods
        mock_stats_calculator.calculate_ppsa.return_value = 1.2  # Mock PPSA value
        mock_stats_calculator.calculate_scoring_distribution.return_value = {
            "ft_pct": 0.2,
            "fg2_pct": 0.5,
            "fg3_pct": 0.3,
        }

        report_generator = ReportGenerator(db_session, mock_stats_calculator)

        # Provide quarter_stats as a list of MagicMock objects with required attributes
        quarter_stats = []
        for i in range(2):
            qs = MagicMock()
            qs.ftm = 2
            qs.fta = 3
            qs.fg2m = 4
            qs.fg2a = 5
            qs.fg3m = 1
            qs.fg3a = 2
            quarter_stats.append(qs)

        # Pass through _handle_missing_quarter_data to match production usage
        player_box_score, _, _ = report_generator._calculate_player_box_score(
            player, pgs, report_generator._handle_missing_quarter_data(quarter_stats), playing_team, opponent_team
        )

        # Check that new stats are included
        assert "ppsa" in player_box_score
        assert "scoring_distribution" in player_box_score
        assert mock_stats_calculator.calculate_ppsa.called
        assert mock_stats_calculator.calculate_scoring_distribution.called

        # Check the expected values
        assert player_box_score["ppsa"] == 1.2
        assert player_box_score["scoring_distribution"]["ft_pct"] == 0.2
        assert player_box_score["scoring_distribution"]["fg2_pct"] == 0.5
        assert player_box_score["scoring_distribution"]["fg3_pct"] == 0.3

    def test_team_totals_with_new_stats(self, db_session, mock_stats_calculator):
        """Test that team totals include PPSA and scoring distribution."""
        report_generator = ReportGenerator(db_session, mock_stats_calculator)

        # Set up test data
        team_totals = report_generator._initialize_team_totals()
        team_totals["points"] = 100
        team_totals["ftm"] = 20
        team_totals["fta"] = 25
        team_totals["fg2m"] = 30
        team_totals["fg2a"] = 50
        team_totals["fg3m"] = 10
        team_totals["fg3a"] = 25
        team_totals["total_fgm"] = 40
        team_totals["total_fga"] = 75

        # Add mocks for the new statistics methods
        mock_stats_calculator.calculate_ppsa.return_value = 1.0  # Mock PPSA value
        mock_stats_calculator.calculate_scoring_distribution.return_value = {
            "ft_pct": 0.2,
            "fg2_pct": 0.6,
            "fg3_pct": 0.2,
        }

        # Calculate team percentages including new stats
        report_generator._calculate_team_percentages(team_totals)

        # Check that new stats are included
        assert "ppsa" in team_totals
        assert "scoring_distribution" in team_totals
        assert mock_stats_calculator.calculate_ppsa.called
        assert mock_stats_calculator.calculate_scoring_distribution.called

        # Check the expected values
        assert team_totals["ppsa"] == 1.0
        assert team_totals["scoring_distribution"]["ft_pct"] == 0.2
        assert team_totals["scoring_distribution"]["fg2_pct"] == 0.6
        assert team_totals["scoring_distribution"]["fg3_pct"] == 0.2

    @patch("app.reports.report_generator.crud_player_game_stats")
    @patch("app.reports.report_generator.crud_player_quarter_stats")
    @patch("app.reports.report_generator.crud_player")
    def test_player_performance_report(
        self,
        mock_crud_player,
        mock_crud_pqs,
        mock_crud_pgs,
        db_session,
        mock_stats_calculator,
        mock_game_data,
        mock_quarter_stats,
    ):
        """Test the new player performance report."""
        # Set up mocks
        player = mock_game_data["players"][0]
        game = mock_game_data["game"]
        pgs = mock_game_data["player_game_stats"][0]

        mock_crud_player.get_player_by_id.return_value = player
        mock_crud_pgs.get_player_game_stats.return_value = pgs
        # Provide MagicMock objects for all four quarters for the player
        mock_quarters = [
            MagicMock(player_game_stats_id=pgs.id, quarter=q, ftm=1, fta=2, fg2m=2, fg2a=4, fg3m=1, fg3a=2)
            for q in range(1, 5)
        ]
        mock_crud_pqs.get_player_quarter_stats.return_value = mock_quarters

        # Create the report generator
        report_generator = ReportGenerator(db_session, mock_stats_calculator)

        # Patch fetch_game_and_teams to return our mock data
        with patch.object(report_generator, "_fetch_game_and_teams") as mock_fetch:
            mock_fetch.return_value = (game, mock_game_data["teams"][0], mock_game_data["teams"][1])

            # Generate the player performance report
            report = report_generator.generate_player_performance_report(player.id, game.id)

            # Check the report structure
            assert isinstance(report, dict)
            assert "name" in report
            assert "quarter_breakdown" in report
            assert isinstance(report["quarter_breakdown"], list)

            # Verify that we called the correct methods
            mock_fetch.assert_called_once_with(game.id)
            mock_crud_player.get_player_by_id.assert_called_once_with(db_session, player.id)
            mock_crud_pgs.get_player_game_stats.assert_called_once_with(db_session, player.id, game.id)
            mock_crud_pqs.get_player_quarter_stats.assert_called_once_with(db_session, pgs.id)

    @patch("app.reports.report_generator.crud_player_game_stats")
    @patch("app.reports.report_generator.crud_player_quarter_stats")
    @patch("app.reports.report_generator.crud_player")
    def test_game_flow_report(
        self,
        mock_crud_player,
        mock_crud_pqs,
        mock_crud_pgs,
        db_session,
        mock_stats_calculator,
        mock_game_data,
        mock_quarter_stats,
    ):
        """Test the new game flow report."""
        # Set up mocks
        game = mock_game_data["game"]
        mock_crud_pgs.get_player_game_stats_by_game.return_value = mock_game_data["player_game_stats"]

        # Set up player mock
        mock_crud_player.get_player_by_id.side_effect = lambda session, player_id: next(
            (p for p in mock_game_data["players"] if p.id == player_id), None
        )

        # Set up quarter stats mock
        def mock_get_quarter_stats(session, pgs_id):
            # Create some quarter stats data
            qs_data = []
            for q in range(1, 5):
                qs = MagicMock(
                    player_game_stats_id=pgs_id,
                    quarter_number=q,
                    ftm=1,
                    fta=2,
                    fg2m=2 if q == 2 else 1,
                    fg2a=4,
                    fg3m=1,
                    fg3a=3,
                )
                qs_data.append(qs)
            return qs_data

        mock_crud_pqs.get_player_quarter_stats.side_effect = mock_get_quarter_stats

        # Create the report generator
        report_generator = ReportGenerator(db_session, mock_stats_calculator)

        # Patch fetch_game_and_teams to return our mock data
        with patch.object(report_generator, "_fetch_game_and_teams") as mock_fetch:
            mock_fetch.return_value = (game, mock_game_data["teams"][0], mock_game_data["teams"][1])

            # Generate the game flow report
            report = report_generator.generate_game_flow_report(game.id)

            # Check the report structure
            assert isinstance(report, dict)
            assert "playing_team" in report
            assert "opponent_team" in report
            assert "point_differentials" in report
            assert "scoring_runs" in report

            # Check that each team has quarter scoring
            assert "quarter_scoring" in report["playing_team"]
            assert "quarter_scoring" in report["opponent_team"]

            # Verify all quarters are represented
            for q in range(1, 5):
                assert q in report["playing_team"]["quarter_scoring"]
                assert q in report["opponent_team"]["quarter_scoring"]
                assert q in report["point_differentials"]

            # Verify that we called the correct methods
            mock_fetch.assert_called_once_with(game.id)
            mock_crud_pgs.get_player_game_stats_by_game.assert_called_once_with(db_session, game.id)

    @patch("app.reports.report_generator.crud_player_game_stats")
    @patch("app.reports.report_generator.crud_player_quarter_stats")
    @patch("app.reports.report_generator.crud_player")
    def test_team_efficiency_report(
        self, mock_crud_player, mock_crud_pqs, mock_crud_pgs, db_session, mock_stats_calculator, mock_game_data
    ):
        """Test the new team efficiency report."""
        # Set up mocks
        team = mock_game_data["teams"][0]  # Using Team A
        game = mock_game_data["game"]

        # Set up player mock
        mock_crud_player.get_player_by_id.side_effect = lambda session, player_id: next(
            (p for p in mock_game_data["players"] if p.id == player_id), None
        )

        # Set up player game stats mock
        mock_crud_pgs.get_player_game_stats_by_game.return_value = [
            pgs for pgs in mock_game_data["player_game_stats"] if pgs.player_id in (1, 2)  # Team A players
        ]

        # Set up quarter stats mock
        def mock_get_quarter_stats(session, pgs_id):
            # Create some mock quarter stats data for all four quarters
            quarters = [
                MagicMock(player_game_stats_id=pgs_id, quarter=q, ftm=1, fta=2, fg2m=2, fg2a=3, fg3m=1, fg3a=2)
                for q in range(1, 5)
            ]
            return quarters

        mock_crud_pqs.get_player_quarter_stats.side_effect = mock_get_quarter_stats

        # Create the report generator
        report_generator = ReportGenerator(db_session, mock_stats_calculator)

        # Patch fetch_game_and_teams to return our mock data
        with patch.object(report_generator, "_fetch_game_and_teams") as mock_fetch:
            mock_fetch.return_value = (game, mock_game_data["teams"][0], mock_game_data["teams"][1])

            # Generate the team efficiency report
            report = report_generator.generate_team_efficiency_report(team.id, game.id)

            # Check the report structure
            assert isinstance(report, dict)
            assert "team_name" in report
            assert "team_ts_pct" in report
            assert "team_efg" in report
            assert "team_ppsa" in report
            assert "scoring_distribution" in report
            assert "player_efficiency" in report
            assert isinstance(report["player_efficiency"], list)

            # Verify each player has efficiency metrics
            for player_data in report["player_efficiency"]:
                assert "name" in player_data
                assert "jersey" in player_data
                assert "points" in player_data
                assert "ts_pct" in player_data
                assert "efg" in player_data
                assert "ppsa" in player_data

            # Verify that we called the correct methods
            mock_fetch.assert_called_once_with(game.id)
            mock_crud_pgs.get_player_game_stats_by_game.assert_called_once_with(db_session, game.id)

    @patch("app.reports.report_generator.crud_player_game_stats")
    @patch("app.reports.report_generator.crud_player_quarter_stats")
    @patch("app.reports.report_generator.crud_player")
    def test_scoring_analysis_report(
        self, mock_crud_player, mock_crud_pqs, mock_crud_pgs, db_session, mock_stats_calculator, mock_game_data
    ):
        """Test the new scoring analysis report."""
        # Set up mocks
        team = mock_game_data["teams"][0]  # Using Team A
        game = mock_game_data["game"]

        # Set up player mock
        mock_crud_player.get_player_by_id.side_effect = lambda session, player_id: next(
            (p for p in mock_game_data["players"] if p.id == player_id), None
        )

        # Set up player game stats mock
        team_a_player_stats = [
            pgs for pgs in mock_game_data["player_game_stats"] if pgs.player_id in (1, 2)  # Team A players
        ]
        mock_crud_pgs.get_player_game_stats_by_game.return_value = team_a_player_stats

        # Set up quarter stats mock
        def mock_get_quarter_stats(session, pgs_id):
            # Create some mock quarter stats data for all four quarters
            quarters = [
                MagicMock(player_game_stats_id=pgs_id, quarter=q, ftm=1, fta=2, fg2m=2, fg2a=3, fg3m=1, fg3a=2)
                for q in range(1, 5)
            ]
            return quarters

        mock_crud_pqs.get_player_quarter_stats.side_effect = mock_get_quarter_stats

        # Create the report generator
        report_generator = ReportGenerator(db_session, mock_stats_calculator)

        # Set up mock for stats_calculator methods
        mock_stats_calculator.calculate_scoring_distribution.return_value = {
            "ft_pct": 0.2,
            "fg2_pct": 0.5,
            "fg3_pct": 0.3,
        }

        # Patch fetch_game_and_teams to return our mock data
        with patch.object(report_generator, "_fetch_game_and_teams") as mock_fetch:
            mock_fetch.return_value = (game, mock_game_data["teams"][0], mock_game_data["teams"][1])

            # Generate the scoring analysis report
            report = report_generator.generate_scoring_analysis_report(team.id, game.id)

            # Check the report structure
            assert isinstance(report, dict)
            assert "team_name" in report
            assert "opponent_name" in report
            assert "team_points" in report
            assert "ft_points" in report
            assert "fg2_points" in report
            assert "fg3_points" in report
            assert "scoring_distribution" in report
            assert "quarter_scoring" in report
            assert "player_scoring" in report

            # Verify quarters are present
            assert isinstance(report["quarter_scoring"], dict)
            for q in range(1, 5):
                assert q in report["quarter_scoring"]

            # Verify player scoring data
            assert isinstance(report["player_scoring"], list)
            for player_data in report["player_scoring"]:
                assert "name" in player_data
                assert "jersey" in player_data
                assert "total_points" in player_data
                assert "ft_points" in player_data
                assert "fg2_points" in player_data
                assert "fg3_points" in player_data
                assert "scoring_distribution" in player_data
                assert "quarter_points" in player_data
                assert isinstance(player_data["quarter_points"], dict)

            # Verify that we called the correct methods
            mock_fetch.assert_called_once_with(game.id)
            mock_crud_pgs.get_player_game_stats_by_game.assert_called_once_with(db_session, game.id)
