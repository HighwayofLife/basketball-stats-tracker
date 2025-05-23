"""Unit tests for player season stats CRUD operations."""

from sqlalchemy.orm import Session

from app.data_access.crud.crud_player_season_stats import (
    create_player_season_stats,
    delete_player_season_stats,
    get_player_all_seasons,
    get_player_season_stats,
    get_season_players,
    update_player_season_stats,
)
from app.data_access.models import Player, PlayerSeasonStats, Team


class TestPlayerSeasonStatsCRUD:
    """Test cases for player season stats CRUD operations."""

    def test_create_player_season_stats(self, db_session: Session):
        """Test creating player season statistics."""
        # Create a team and player first
        team = Team(name="Test Team")
        db_session.add(team)
        db_session.commit()

        player = Player(name="Test Player", team_id=team.id, jersey_number=10)
        db_session.add(player)
        db_session.commit()

        # Create season stats
        season_stats = create_player_season_stats(db_session, player.id, "2024-2025")

        assert season_stats is not None
        assert season_stats.player_id == player.id
        assert season_stats.season == "2024-2025"
        assert season_stats.games_played == 0
        assert season_stats.total_fouls == 0
        assert season_stats.total_ftm == 0
        assert season_stats.total_fta == 0
        assert season_stats.total_2pm == 0
        assert season_stats.total_2pa == 0
        assert season_stats.total_3pm == 0
        assert season_stats.total_3pa == 0

    def test_get_player_season_stats(self, db_session: Session):
        """Test retrieving player season statistics."""
        # Create test data
        team = Team(name="Test Team")
        db_session.add(team)
        db_session.commit()

        player = Player(name="Test Player", team_id=team.id, jersey_number=10)
        db_session.add(player)
        db_session.commit()

        season_stats = PlayerSeasonStats(
            player_id=player.id,
            season="2024-2025",
            games_played=10,
            total_fouls=20,
            total_ftm=30,
            total_fta=40,
            total_2pm=50,
            total_2pa=60,
            total_3pm=15,
            total_3pa=25,
        )
        db_session.add(season_stats)
        db_session.commit()

        # Test retrieval
        retrieved = get_player_season_stats(db_session, player.id, "2024-2025")

        assert retrieved is not None
        assert retrieved.player_id == player.id
        assert retrieved.season == "2024-2025"
        assert retrieved.games_played == 10
        assert retrieved.total_fouls == 20
        assert retrieved.total_ftm == 30

    def test_get_player_season_stats_not_found(self, db_session: Session):
        """Test retrieving non-existent player season statistics."""
        result = get_player_season_stats(db_session, 999, "2024-2025")
        assert result is None

    def test_get_player_all_seasons(self, db_session: Session):
        """Test retrieving all seasons for a player."""
        # Create test data
        team = Team(name="Test Team")
        db_session.add(team)
        db_session.commit()

        player = Player(name="Test Player", team_id=team.id, jersey_number=10)
        db_session.add(player)
        db_session.commit()

        # Add multiple seasons
        for season in ["2022-2023", "2023-2024", "2024-2025"]:
            stats = PlayerSeasonStats(player_id=player.id, season=season, games_played=10)
            db_session.add(stats)
        db_session.commit()

        # Test retrieval
        all_seasons = get_player_all_seasons(db_session, player.id)

        assert len(all_seasons) == 3
        # Should be ordered by season descending
        assert all_seasons[0].season == "2024-2025"
        assert all_seasons[1].season == "2023-2024"
        assert all_seasons[2].season == "2022-2023"

    def test_get_season_players(self, db_session: Session):
        """Test retrieving all players for a season."""
        # Create test data
        team1 = Team(name="Team A")
        team2 = Team(name="Team B")
        db_session.add_all([team1, team2])
        db_session.commit()

        player1 = Player(name="Player 1", team_id=team1.id, jersey_number=10)
        player2 = Player(name="Player 2", team_id=team1.id, jersey_number=20)
        player3 = Player(name="Player 3", team_id=team2.id, jersey_number=30)
        db_session.add_all([player1, player2, player3])
        db_session.commit()

        # Add season stats for each player
        for player in [player1, player2, player3]:
            stats = PlayerSeasonStats(player_id=player.id, season="2024-2025", games_played=5)
            db_session.add(stats)
        db_session.commit()

        # Test retrieval without team filter
        all_players = get_season_players(db_session, "2024-2025")
        assert len(all_players) == 3

        # Test retrieval with team filter
        team1_players = get_season_players(db_session, "2024-2025", team_id=team1.id)
        assert len(team1_players) == 2
        assert all(ps.player.team_id == team1.id for ps in team1_players)

    def test_update_player_season_stats(self, db_session: Session):
        """Test updating player season statistics."""
        # Create test data
        team = Team(name="Test Team")
        db_session.add(team)
        db_session.commit()

        player = Player(name="Test Player", team_id=team.id, jersey_number=10)
        db_session.add(player)
        db_session.commit()

        season_stats = PlayerSeasonStats(player_id=player.id, season="2024-2025", games_played=10, total_fouls=20)
        db_session.add(season_stats)
        db_session.commit()

        # Update stats
        updated = update_player_season_stats(
            db_session, player.id, "2024-2025", games_played=15, total_fouls=25, total_ftm=40, total_fta=50
        )

        assert updated is not None
        assert updated.games_played == 15
        assert updated.total_fouls == 25
        assert updated.total_ftm == 40
        assert updated.total_fta == 50

    def test_update_player_season_stats_not_found(self, db_session: Session):
        """Test updating non-existent player season statistics."""
        result = update_player_season_stats(db_session, 999, "2024-2025", games_played=10)
        assert result is None

    def test_delete_player_season_stats(self, db_session: Session):
        """Test deleting player season statistics."""
        # Create test data
        team = Team(name="Test Team")
        db_session.add(team)
        db_session.commit()

        player = Player(name="Test Player", team_id=team.id, jersey_number=10)
        db_session.add(player)
        db_session.commit()

        season_stats = PlayerSeasonStats(player_id=player.id, season="2024-2025", games_played=10)
        db_session.add(season_stats)
        db_session.commit()

        # Delete stats
        result = delete_player_season_stats(db_session, player.id, "2024-2025")
        assert result is True

        # Verify deletion
        retrieved = get_player_season_stats(db_session, player.id, "2024-2025")
        assert retrieved is None

    def test_delete_player_season_stats_not_found(self, db_session: Session):
        """Test deleting non-existent player season statistics."""
        result = delete_player_season_stats(db_session, 999, "2024-2025")
        assert result is False
