"""Unit tests for team season stats CRUD operations."""

from sqlalchemy.orm import Session

from app.data_access.crud.crud_team_season_stats import (
    create_team_season_stats,
    delete_team_season_stats,
    get_season_teams,
    get_team_all_seasons,
    get_team_season_stats,
    update_team_season_stats,
)
from app.data_access.models import Team, TeamSeasonStats


class TestTeamSeasonStatsCRUD:
    """Test cases for team season stats CRUD operations."""

    def test_create_team_season_stats(self, db_session: Session):
        """Test creating team season statistics."""
        # Create a team first
        team = Team(name="Test Team")
        db_session.add(team)
        db_session.commit()

        # Create season stats
        season_stats = create_team_season_stats(db_session, team.id, "2024-2025")

        assert season_stats is not None
        assert season_stats.team_id == team.id
        assert season_stats.season == "2024-2025"
        assert season_stats.games_played == 0
        assert season_stats.wins == 0
        assert season_stats.losses == 0
        assert season_stats.total_points_for == 0
        assert season_stats.total_points_against == 0
        assert season_stats.total_ftm == 0
        assert season_stats.total_fta == 0
        assert season_stats.total_2pm == 0
        assert season_stats.total_2pa == 0
        assert season_stats.total_3pm == 0
        assert season_stats.total_3pa == 0

    def test_get_team_season_stats(self, db_session: Session):
        """Test retrieving team season statistics."""
        # Create test data
        team = Team(name="Test Team")
        db_session.add(team)
        db_session.commit()

        season_stats = TeamSeasonStats(
            team_id=team.id,
            season="2024-2025",
            games_played=20,
            wins=15,
            losses=5,
            total_points_for=1600,
            total_points_against=1400,
            total_ftm=300,
            total_fta=400,
            total_2pm=500,
            total_2pa=600,
            total_3pm=150,
            total_3pa=250,
        )
        db_session.add(season_stats)
        db_session.commit()

        # Test retrieval
        retrieved = get_team_season_stats(db_session, team.id, "2024-2025")

        assert retrieved is not None
        assert retrieved.team_id == team.id
        assert retrieved.season == "2024-2025"
        assert retrieved.games_played == 20
        assert retrieved.wins == 15
        assert retrieved.losses == 5
        assert retrieved.total_points_for == 1600

    def test_get_team_season_stats_not_found(self, db_session: Session):
        """Test retrieving non-existent team season statistics."""
        result = get_team_season_stats(db_session, 999, "2024-2025")
        assert result is None

    def test_get_team_all_seasons(self, db_session: Session):
        """Test retrieving all seasons for a team."""
        # Create test data
        team = Team(name="Test Team")
        db_session.add(team)
        db_session.commit()

        # Add multiple seasons
        for i, season in enumerate(["2022-2023", "2023-2024", "2024-2025"]):
            stats = TeamSeasonStats(team_id=team.id, season=season, games_played=20, wins=10 + i, losses=10 - i)
            db_session.add(stats)
        db_session.commit()

        # Test retrieval
        all_seasons = get_team_all_seasons(db_session, team.id)

        assert len(all_seasons) == 3
        # Should be ordered by season descending
        assert all_seasons[0].season == "2024-2025"
        assert all_seasons[1].season == "2023-2024"
        assert all_seasons[2].season == "2022-2023"

    def test_get_season_teams(self, db_session: Session):
        """Test retrieving all teams for a season."""
        # Create test data
        team1 = Team(name="Team A")
        team2 = Team(name="Team B")
        team3 = Team(name="Team C")
        db_session.add_all([team1, team2, team3])
        db_session.commit()

        # Add season stats for each team
        for i, team in enumerate([team1, team2, team3]):
            stats = TeamSeasonStats(
                team_id=team.id, season="2024-2025", games_played=20, wins=15 - i * 3, losses=5 + i * 3
            )
            db_session.add(stats)
        db_session.commit()

        # Test retrieval
        all_teams = get_season_teams(db_session, "2024-2025")
        assert len(all_teams) == 3
        assert all(ts.season == "2024-2025" for ts in all_teams)

    def test_update_team_season_stats(self, db_session: Session):
        """Test updating team season statistics."""
        # Create test data
        team = Team(name="Test Team")
        db_session.add(team)
        db_session.commit()

        season_stats = TeamSeasonStats(team_id=team.id, season="2024-2025", games_played=10, wins=6, losses=4)
        db_session.add(season_stats)
        db_session.commit()

        # Update stats
        updated = update_team_season_stats(
            db_session,
            team.id,
            "2024-2025",
            games_played=15,
            wins=10,
            losses=5,
            total_points_for=1200,
            total_points_against=1100,
        )

        assert updated is not None
        assert updated.games_played == 15
        assert updated.wins == 10
        assert updated.losses == 5
        assert updated.total_points_for == 1200
        assert updated.total_points_against == 1100

    def test_update_team_season_stats_partial(self, db_session: Session):
        """Test partial update of team season statistics."""
        # Create test data
        team = Team(name="Test Team")
        db_session.add(team)
        db_session.commit()

        season_stats = TeamSeasonStats(
            team_id=team.id, season="2024-2025", games_played=10, wins=6, losses=4, total_ftm=100, total_fta=120
        )
        db_session.add(season_stats)
        db_session.commit()

        # Update only some fields
        updated = update_team_season_stats(db_session, team.id, "2024-2025", total_ftm=150, total_fta=180)

        assert updated is not None
        # Unchanged fields
        assert updated.games_played == 10
        assert updated.wins == 6
        assert updated.losses == 4
        # Updated fields
        assert updated.total_ftm == 150
        assert updated.total_fta == 180

    def test_update_team_season_stats_not_found(self, db_session: Session):
        """Test updating non-existent team season statistics."""
        result = update_team_season_stats(db_session, 999, "2024-2025", games_played=10)
        assert result is None

    def test_delete_team_season_stats(self, db_session: Session):
        """Test deleting team season statistics."""
        # Create test data
        team = Team(name="Test Team")
        db_session.add(team)
        db_session.commit()

        season_stats = TeamSeasonStats(team_id=team.id, season="2024-2025", games_played=10)
        db_session.add(season_stats)
        db_session.commit()

        # Delete stats
        result = delete_team_season_stats(db_session, team.id, "2024-2025")
        assert result is True

        # Verify deletion
        retrieved = get_team_season_stats(db_session, team.id, "2024-2025")
        assert retrieved is None

    def test_delete_team_season_stats_not_found(self, db_session: Session):
        """Test deleting non-existent team season statistics."""
        result = delete_team_season_stats(db_session, 999, "2024-2025")
        assert result is False
