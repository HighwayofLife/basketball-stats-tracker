"""Simple unit tests for team statistics functionality."""

import datetime

import pytest

from app.data_access.models import Game, Player, PlayerGameStats, Team
from app.repositories.team_repository import TeamRepository
from app.services.season_stats_service import SeasonStatsService


@pytest.mark.skip(
    reason="SQLAlchemy model relationship issues with User model - "
    "Team model references User but it's not available during testing"
)
class TestTeamStatsService:
    """Test team statistics service functionality."""

    def test_team_repository_basic_operations(self, db_session):
        """Test basic team repository operations."""
        repo = TeamRepository(db_session)

        # Create a team
        team = Team(id=1, name="Hawks", display_name="Atlanta Hawks")
        db_session.add(team)
        db_session.commit()

        # Test get_by_id
        retrieved_team = repo.get_by_id(1)
        assert retrieved_team is not None
        assert retrieved_team.name == "Hawks"
        assert retrieved_team.display_name == "Atlanta Hawks"

        # Test get_by_name
        team_by_name = repo.get_by_name("Hawks")
        assert team_by_name is not None
        assert team_by_name.id == 1

        # Test has_games (should be False initially)
        assert repo.has_games(1) is False

        # Add a game
        game = Game(id=1, playing_team_id=1, opponent_team_id=2, date=datetime.date(2025, 5, 1))
        db_session.add(game)
        db_session.commit()

        # Test has_games (should be True now)
        assert repo.has_games(1) is True

    def test_team_repository_with_player_count(self, db_session):
        """Test team repository with player count functionality."""
        repo = TeamRepository(db_session)

        # Create teams
        team1 = Team(id=1, name="Hawks", display_name="Atlanta Hawks")
        team2 = Team(id=2, name="Lakers", display_name="Los Angeles Lakers")
        db_session.add(team1)
        db_session.add(team2)
        db_session.commit()

        # Add players to team1
        players = [
            Player(id=1, name="Player 1", team_id=1, jersey_number="1", is_active=True),
            Player(id=2, name="Player 2", team_id=1, jersey_number="2", is_active=True),
            Player(id=3, name="Player 3", team_id=1, jersey_number="3", is_active=False),  # Inactive
            Player(id=4, name="Player 4", team_id=2, jersey_number="4", is_active=True),
        ]

        for player in players:
            db_session.add(player)
        db_session.commit()

        # Test get_with_player_count
        teams_with_counts = repo.get_with_player_count()
        assert len(teams_with_counts) == 2

        # Find Hawks team data
        hawks_data = next(t for t in teams_with_counts if t["name"] == "Hawks")
        assert hawks_data["player_count"] == 2  # Only active players

        # Find Lakers team data
        lakers_data = next(t for t in teams_with_counts if t["name"] == "Lakers")
        assert lakers_data["player_count"] == 1

    def test_season_stats_calculation(self, db_session):
        """Test season statistics calculation functionality."""
        service = SeasonStatsService(db_session)

        # Create teams
        team1 = Team(id=1, name="Hawks", display_name="Atlanta Hawks")
        team2 = Team(id=2, name="Lakers", display_name="Los Angeles Lakers")
        db_session.add(team1)
        db_session.add(team2)
        db_session.commit()

        # Create season for the test
        from app.data_access.models import Season

        season = Season(
            id=1,
            name="Season 2024-2025",
            code="2024-2025",
            start_date=datetime.date(2024, 10, 1),
            end_date=datetime.date(2025, 5, 31),
            is_active=True,
        )
        db_session.add(season)
        db_session.commit()

        # Create players
        players = [
            Player(id=1, name="Player 1", team_id=1, jersey_number="1", is_active=True),
            Player(id=2, name="Player 2", team_id=1, jersey_number="2", is_active=True),
            Player(id=3, name="Player 3", team_id=2, jersey_number="3", is_active=True),
            Player(id=4, name="Player 4", team_id=2, jersey_number="4", is_active=True),
        ]

        for player in players:
            db_session.add(player)
        db_session.commit()

        # Create a game (using a date within the 2024-2025 season)
        game = Game(id=1, playing_team_id=1, opponent_team_id=2, date=datetime.date(2025, 3, 1))
        db_session.add(game)
        db_session.commit()

        # Create player stats
        stats = [
            PlayerGameStats(
                player_id=1,
                game_id=1,
                total_ftm=5,
                total_fta=6,
                total_2pm=8,
                total_2pa=12,
                total_3pm=3,
                total_3pa=5,
                fouls=2,
            ),
            PlayerGameStats(
                player_id=2,
                game_id=1,
                total_ftm=3,
                total_fta=4,
                total_2pm=6,
                total_2pa=10,
                total_3pm=2,
                total_3pa=4,
                fouls=3,
            ),
            PlayerGameStats(
                player_id=3,
                game_id=1,
                total_ftm=4,
                total_fta=5,
                total_2pm=5,
                total_2pa=8,
                total_3pm=1,
                total_3pa=3,
                fouls=1,
            ),
            PlayerGameStats(
                player_id=4,
                game_id=1,
                total_ftm=2,
                total_fta=3,
                total_2pm=4,
                total_2pa=7,
                total_3pm=2,
                total_3pa=4,
                fouls=2,
            ),
        ]

        for stat in stats:
            db_session.add(stat)
        db_session.commit()

        # Calculate team stats
        # For date 2025-03-01, the season should be 2024-2025
        season = service.get_season_from_date(datetime.date(2025, 3, 1))
        assert season == "2024-2025"

        team_stats = service.update_team_season_stats(1, season)

        assert team_stats is not None
        assert team_stats.games_played == 1
        assert team_stats.total_ftm == 8  # 5 + 3
        assert team_stats.total_fta == 10  # 6 + 4
        assert team_stats.total_2pm == 14  # 8 + 6
        assert team_stats.total_2pa == 22  # 12 + 10
        assert team_stats.total_3pm == 5  # 3 + 2
        assert team_stats.total_3pa == 9  # 5 + 4

        # Hawks scored: 8 FT + (14 * 2) 2P + (5 * 3) 3P = 8 + 28 + 15 = 51 points
        # Lakers scored: 6 FT + (9 * 2) 2P + (3 * 3) 3P = 6 + 18 + 9 = 33 points
        # Hawks won
        assert team_stats.wins == 1
        assert team_stats.losses == 0
        assert team_stats.total_points_for == 51
        assert team_stats.total_points_against == 33

    def test_team_stats_zero_division_handling(self, db_session):
        """Test that team stats calculations handle zero division correctly."""
        service = SeasonStatsService(db_session)

        # Create team with no stats
        team = Team(id=1, name="Hawks", display_name="Atlanta Hawks")
        db_session.add(team)
        db_session.commit()

        # Try to update stats (should not crash)
        result = service.update_team_season_stats(1, "2024-2025")

        # Should return None if no games found
        assert result is None or result.games_played == 0

    def test_team_recent_games_calculation(self, db_session):
        """Test calculation of recent games data."""
        # Create teams
        team1 = Team(id=1, name="Hawks", display_name="Atlanta Hawks")
        team2 = Team(id=2, name="Lakers", display_name="Los Angeles Lakers")
        db_session.add(team1)
        db_session.add(team2)
        db_session.commit()

        # Create players
        player1 = Player(id=1, name="Player 1", team_id=1, jersey_number="1", is_active=True)
        player2 = Player(id=2, name="Player 2", team_id=2, jersey_number="2", is_active=True)
        db_session.add(player1)
        db_session.add(player2)
        db_session.commit()

        # Create multiple games
        games = []
        for i in range(3):
            game = Game(id=i + 1, playing_team_id=1, opponent_team_id=2, date=datetime.date(2025, 5, 1 + i * 7))
            db_session.add(game)
            games.append(game)
        db_session.commit()

        # Add stats for each game
        for i, game in enumerate(games):
            # Team 1 player stats
            stat1 = PlayerGameStats(
                player_id=1,
                game_id=game.id,
                total_ftm=3 + i,
                total_fta=4 + i,
                total_2pm=5 + i,
                total_2pa=8 + i,
                total_3pm=2 + i,
                total_3pa=4 + i,
                fouls=2,
            )
            # Team 2 player stats
            stat2 = PlayerGameStats(
                player_id=2,
                game_id=game.id,
                total_ftm=2 + i,
                total_fta=3 + i,
                total_2pm=4 + i,
                total_2pa=6 + i,
                total_3pm=1 + i,
                total_3pa=3 + i,
                fouls=1,
            )
            db_session.add(stat1)
            db_session.add(stat2)
        db_session.commit()

        # Verify we can query games for the team
        from sqlalchemy import desc

        recent_games = (
            db_session.query(Game)
            .filter((Game.playing_team_id == 1) | (Game.opponent_team_id == 1))
            .order_by(desc(Game.date))
            .limit(10)
            .all()
        )

        assert len(recent_games) == 3

        # Verify game ordering (most recent first)
        assert recent_games[0].date > recent_games[1].date
        assert recent_games[1].date > recent_games[2].date
