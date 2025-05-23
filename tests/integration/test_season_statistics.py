"""Integration tests for season statistics functionality."""

from datetime import date

import pytest
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from app.cli import cli
from app.data_access.crud import (
    create_game,
    create_player,
    create_player_game_stats,
    create_team,
    get_player_season_stats,
    get_team_season_stats,
)
from app.services.season_stats_service import SeasonStatsService
from app.utils.stats_calculator import StatsCalculator


@pytest.fixture
def cli_runner():
    """Returns a CLI runner for testing CLI commands."""
    return CliRunner()


class TestSeasonStatisticsIntegration:
    """Integration tests for season statistics functionality."""

    @pytest.fixture
    def setup_test_data(self, db_session: Session):
        """Set up test data for integration tests."""
        # Create teams
        team1 = create_team(db_session, "Lakers")
        team2 = create_team(db_session, "Warriors")

        # Create players
        player1 = create_player(db_session, team1.id, "LeBron James", 23)
        player2 = create_player(db_session, team1.id, "Anthony Davis", 3)
        player3 = create_player(db_session, team2.id, "Stephen Curry", 30)
        player4 = create_player(db_session, team2.id, "Klay Thompson", 11)

        # Create games
        game1 = create_game(db_session, date(2024, 11, 1), team1.id, team2.id)
        game2 = create_game(db_session, date(2024, 11, 5), team2.id, team1.id)

        # Create game stats for game 1 (Lakers home)
        # Lakers players
        create_player_game_stats(
            db_session,
            game1.id,
            player1.id,
            fouls=3,
            total_ftm=8,
            total_fta=10,
            total_2pm=10,
            total_2pa=15,
            total_3pm=2,
            total_3pa=6,
        )
        create_player_game_stats(
            db_session,
            game1.id,
            player2.id,
            fouls=2,
            total_ftm=6,
            total_fta=8,
            total_2pm=12,
            total_2pa=18,
            total_3pm=0,
            total_3pa=2,
        )
        # Warriors players
        create_player_game_stats(
            db_session,
            game1.id,
            player3.id,
            fouls=2,
            total_ftm=10,
            total_fta=10,
            total_2pm=6,
            total_2pa=10,
            total_3pm=8,
            total_3pa=14,
        )
        create_player_game_stats(
            db_session,
            game1.id,
            player4.id,
            fouls=4,
            total_ftm=4,
            total_fta=6,
            total_2pm=8,
            total_2pa=12,
            total_3pm=5,
            total_3pa=10,
        )

        # Create game stats for game 2 (Warriors home)
        # Lakers players
        create_player_game_stats(
            db_session,
            game2.id,
            player1.id,
            fouls=4,
            total_ftm=6,
            total_fta=8,
            total_2pm=12,
            total_2pa=18,
            total_3pm=3,
            total_3pa=8,
        )
        create_player_game_stats(
            db_session,
            game2.id,
            player2.id,
            fouls=3,
            total_ftm=8,
            total_fta=10,
            total_2pm=10,
            total_2pa=14,
            total_3pm=1,
            total_3pa=3,
        )
        # Warriors players
        create_player_game_stats(
            db_session,
            game2.id,
            player3.id,
            fouls=1,
            total_ftm=8,
            total_fta=8,
            total_2pm=8,
            total_2pa=12,
            total_3pm=10,
            total_3pa=16,
        )
        create_player_game_stats(
            db_session,
            game2.id,
            player4.id,
            fouls=3,
            total_ftm=2,
            total_fta=4,
            total_2pm=6,
            total_2pa=10,
            total_3pm=6,
            total_3pa=12,
        )

        return {
            "teams": {"lakers": team1, "warriors": team2},
            "players": {"lebron": player1, "davis": player2, "curry": player3, "thompson": player4},
            "games": [game1, game2],
        }

    def test_update_season_stats_integration(self, db_session: Session, setup_test_data):
        """Test updating season statistics for all players and teams."""
        stats_calculator = StatsCalculator()
        season_service = SeasonStatsService(db_session, stats_calculator)

        # Update all season stats
        season_service.update_all_season_stats("2024-2025")

        # Check player season stats
        lebron_stats = get_player_season_stats(db_session, setup_test_data["players"]["lebron"].id, "2024-2025")
        assert lebron_stats is not None
        assert lebron_stats.games_played == 2
        assert lebron_stats.total_fouls == 7
        assert lebron_stats.total_ftm == 14
        assert lebron_stats.total_fta == 18
        assert lebron_stats.total_2pm == 22
        assert lebron_stats.total_3pm == 5

        # Check team season stats
        lakers_stats = get_team_season_stats(db_session, setup_test_data["teams"]["lakers"].id, "2024-2025")
        assert lakers_stats is not None
        assert lakers_stats.games_played == 2
        # Lakers scored 64 in game 1 (8+6 FT + 10*2+12*2 2P + 2*3+0*3 3P = 14+44+6=64)
        # Lakers scored 72 in game 2 (6+8 FT + 12*2+10*2 2P + 3*3+1*3 3P = 14+44+12=70)
        # Warriors scored 71 in game 1 (10+4 FT + 6*2+8*2 2P + 8*3+5*3 3P = 14+28+39=81)
        # Warriors scored 68 in game 2 (8+2 FT + 8*2+6*2 2P + 10*3+6*3 3P = 10+28+48=86)
        # So Lakers lost game 1 (64-81) and lost game 2 (70-86)
        assert lakers_stats.wins == 0
        assert lakers_stats.losses == 2

    def test_player_rankings_integration(self, db_session: Session, setup_test_data):
        """Test player rankings functionality."""
        stats_calculator = StatsCalculator()
        season_service = SeasonStatsService(db_session, stats_calculator)

        # Update season stats first
        season_service.update_all_season_stats("2024-2025")

        # Get PPG rankings
        ppg_rankings = season_service.get_player_rankings("ppg", "2024-2025", limit=4)

        assert len(ppg_rankings) == 4
        # Curry should be #1 with highest PPG
        # Game 1: 10 + 6*2 + 8*3 = 10+12+24 = 46
        # Game 2: 8 + 8*2 + 10*3 = 8+16+30 = 54
        # Total: 100 points / 2 games = 50 PPG
        assert ppg_rankings[0]["player_name"] == "Stephen Curry"
        assert ppg_rankings[0]["value"] == 50.0

    def test_team_standings_integration(self, db_session: Session, setup_test_data):
        """Test team standings functionality."""
        stats_calculator = StatsCalculator()
        season_service = SeasonStatsService(db_session, stats_calculator)

        # Update season stats first
        season_service.update_all_season_stats("2024-2025")

        # Get standings
        standings = season_service.get_team_standings("2024-2025")

        assert len(standings) == 2
        # Warriors should be first (2-0)
        assert standings[0]["team_name"] == "Warriors"
        assert standings[0]["wins"] == 2
        assert standings[0]["losses"] == 0
        assert standings[0]["win_pct"] == 1.0
        assert standings[0]["games_back"] is None

        # Lakers should be second (0-2)
        assert standings[1]["team_name"] == "Lakers"
        assert standings[1]["wins"] == 0
        assert standings[1]["losses"] == 2
        assert standings[1]["win_pct"] == 0.0
        assert standings[1]["games_back"] == 2.0

    def test_cli_season_report_standings(self, db_session: Session, setup_test_data, cli_runner: CliRunner):
        """Test CLI season report for standings."""
        # Update season stats first
        stats_calculator = StatsCalculator()
        season_service = SeasonStatsService(db_session, stats_calculator)
        season_service.update_all_season_stats("2024-2025")

        # Run CLI command
        result = cli_runner.invoke(cli, ["season-report", "--type", "standings", "--season", "2024-2025"])

        assert result.exit_code == 0
        assert "Team Standings - 2024-2025" in result.output
        assert "Warriors" in result.output
        assert "Lakers" in result.output
        assert "2" in result.output  # wins
        assert "0" in result.output  # losses

    def test_cli_season_report_player_leaders(self, db_session: Session, setup_test_data, cli_runner: CliRunner):
        """Test CLI season report for player leaders."""
        # Update season stats first
        stats_calculator = StatsCalculator()
        season_service = SeasonStatsService(db_session, stats_calculator)
        season_service.update_all_season_stats("2024-2025")

        # Run CLI command for PPG leaders
        result = cli_runner.invoke(
            cli, ["season-report", "--type", "player-leaders", "--stat", "ppg", "--season", "2024-2025", "--limit", "3"]
        )

        assert result.exit_code == 0
        assert "Player Leaders - Points Per Game" in result.output
        assert "Stephen Curry" in result.output
        assert "50.000" in result.output  # Curry's PPG

    def test_cli_update_season_stats(self, db_session: Session, setup_test_data, cli_runner: CliRunner):
        """Test CLI command to update season statistics."""
        # Run update command
        result = cli_runner.invoke(cli, ["update-season-stats", "--season", "2024-2025"])

        assert result.exit_code == 0
        assert "Updating season statistics for 2024-2025" in result.output
        assert "Season statistics updated successfully!" in result.output

        # Verify stats were created
        lebron_stats = get_player_season_stats(db_session, setup_test_data["players"]["lebron"].id, "2024-2025")
        assert lebron_stats is not None
        assert lebron_stats.games_played == 2

    def test_season_detection(self, db_session: Session):
        """Test automatic season detection based on game dates."""
        stats_calculator = StatsCalculator()
        season_service = SeasonStatsService(db_session, stats_calculator)

        # Test various dates
        assert season_service.get_season_from_date(date(2024, 10, 1)) == "2024-2025"
        assert season_service.get_season_from_date(date(2024, 12, 25)) == "2024-2025"
        assert season_service.get_season_from_date(date(2025, 3, 15)) == "2024-2025"
        assert season_service.get_season_from_date(date(2024, 9, 30)) == "2023-2024"
        assert season_service.get_season_from_date(date(2024, 5, 1)) == "2023-2024"

    def test_csv_export_season_report(self, db_session: Session, setup_test_data, cli_runner: CliRunner, tmp_path):
        """Test CSV export of season reports."""
        # Update season stats first
        stats_calculator = StatsCalculator()
        season_service = SeasonStatsService(db_session, stats_calculator)
        season_service.update_all_season_stats("2024-2025")

        # Export standings to CSV
        csv_file = tmp_path / "standings.csv"
        result = cli_runner.invoke(
            cli,
            [
                "season-report",
                "--type",
                "standings",
                "--season",
                "2024-2025",
                "--format",
                "csv",
                "--output",
                str(csv_file),
            ],
        )

        assert result.exit_code == 0
        assert csv_file.exists()

        # Check CSV content
        content = csv_file.read_text()
        assert "team_name" in content
        assert "wins" in content
        assert "losses" in content
        assert "Warriors" in content
        assert "Lakers" in content
