"""Unit tests for TeamRepository."""

from app.data_access.models import Game, Player, Team
from app.repositories.team_repository import TeamRepository


class TestTeamRepository:
    """Test cases for TeamRepository."""

    def test_get_with_player_count_empty(self, db_session):
        """Test get_with_player_count when no teams exist."""
        repo = TeamRepository(db_session)
        result = repo.get_with_player_count()

        assert result == []

    def test_get_with_player_count_no_players(self, db_session):
        """Test get_with_player_count when teams have no players."""
        repo = TeamRepository(db_session)

        # Create teams with no players
        team1 = Team(id=1, name="Hawks", display_name="Atlanta Hawks")
        team2 = Team(id=2, name="Lakers", display_name="Los Angeles Lakers")
        db_session.add(team1)
        db_session.add(team2)
        db_session.commit()

        result = repo.get_with_player_count()

        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[0]["name"] == "Hawks"
        assert result[0]["display_name"] == "Atlanta Hawks"
        assert result[0]["player_count"] == 0

        assert result[1]["id"] == 2
        assert result[1]["name"] == "Lakers"
        assert result[1]["display_name"] == "Los Angeles Lakers"
        assert result[1]["player_count"] == 0

    def test_get_with_player_count_with_players(self, db_session):
        """Test get_with_player_count when teams have players."""
        repo = TeamRepository(db_session)

        # Create teams
        team1 = Team(id=1, name="Hawks", display_name="Atlanta Hawks")
        team2 = Team(id=2, name="Lakers", display_name="Los Angeles Lakers")
        db_session.add(team1)
        db_session.add(team2)
        db_session.commit()

        # Create players (some active, some inactive)
        players = [
            Player(id=1, name="Player 1", team_id=1, jersey_number="1", is_active=True),
            Player(id=2, name="Player 2", team_id=1, jersey_number="2", is_active=True),
            Player(id=3, name="Player 3", team_id=1, jersey_number="3", is_active=False),  # Inactive
            Player(id=4, name="Player 4", team_id=2, jersey_number="4", is_active=True),
            Player(id=5, name="Player 5", team_id=2, jersey_number="5", is_active=True),
            Player(id=6, name="Player 6", team_id=2, jersey_number="6", is_active=True),
        ]

        for player in players:
            db_session.add(player)
        db_session.commit()

        result = repo.get_with_player_count()

        assert len(result) == 2

        # Hawks should have 2 active players
        hawks_data = next(t for t in result if t["name"] == "Hawks")
        assert hawks_data["player_count"] == 2

        # Lakers should have 3 active players
        lakers_data = next(t for t in result if t["name"] == "Lakers")
        assert lakers_data["player_count"] == 3

    def test_get_by_name_found(self, db_session):
        """Test get_by_name when team exists."""
        repo = TeamRepository(db_session)

        # Create a team
        team = Team(id=1, name="Hawks", display_name="Atlanta Hawks")
        db_session.add(team)
        db_session.commit()

        result = repo.get_by_name("Hawks")

        assert result is not None
        assert result.id == 1
        assert result.name == "Hawks"
        assert result.display_name == "Atlanta Hawks"

    def test_get_by_name_not_found(self, db_session):
        """Test get_by_name when team doesn't exist."""
        repo = TeamRepository(db_session)

        result = repo.get_by_name("NonexistentTeam")

        assert result is None

    def test_has_games_no_games(self, db_session):
        """Test has_games when team has no games."""
        repo = TeamRepository(db_session)

        # Create a team
        team = Team(id=1, name="Hawks", display_name="Atlanta Hawks")
        db_session.add(team)
        db_session.commit()

        result = repo.has_games(1)

        assert result is False

    def test_has_games_as_playing_team(self, db_session):
        """Test has_games when team is the playing team."""
        repo = TeamRepository(db_session)

        # Create teams
        team1 = Team(id=1, name="Hawks", display_name="Atlanta Hawks")
        team2 = Team(id=2, name="Lakers", display_name="Los Angeles Lakers")
        db_session.add(team1)
        db_session.add(team2)
        db_session.commit()

        # Create a game where team1 is playing team
        from datetime import date

        game = Game(id=1, playing_team_id=1, opponent_team_id=2, date=date(2025, 3, 1))
        db_session.add(game)
        db_session.commit()

        result = repo.has_games(1)

        assert result is True

    def test_has_games_as_opponent_team(self, db_session):
        """Test has_games when team is the opponent team."""
        repo = TeamRepository(db_session)

        # Create teams
        team1 = Team(id=1, name="Hawks", display_name="Atlanta Hawks")
        team2 = Team(id=2, name="Lakers", display_name="Los Angeles Lakers")
        db_session.add(team1)
        db_session.add(team2)
        db_session.commit()

        # Create a game where team2 is opponent team
        from datetime import date

        game = Game(id=1, playing_team_id=1, opponent_team_id=2, date=date(2025, 3, 1))
        db_session.add(game)
        db_session.commit()

        result = repo.has_games(2)  # Check team2 (opponent)

        assert result is True

    def test_get_deleted_teams_empty(self, db_session):
        """Test get_deleted_teams when no deleted teams exist."""
        repo = TeamRepository(db_session)

        # Create a normal (non-deleted) team
        team = Team(id=1, name="Hawks", display_name="Atlanta Hawks", is_deleted=False)
        db_session.add(team)
        db_session.commit()

        result = repo.get_deleted_teams()

        assert result == []

    def test_get_deleted_teams_with_deleted(self, db_session):
        """Test get_deleted_teams when deleted teams exist."""
        repo = TeamRepository(db_session)

        from datetime import datetime

        # Create teams (some deleted, some not)
        team1 = Team(id=1, name="Hawks", display_name="Atlanta Hawks", is_deleted=False)
        team2 = Team(
            id=2,
            name="Lakers",
            display_name="Los Angeles Lakers",
            is_deleted=True,
            deleted_at=datetime(2025, 1, 1, 12, 0, 0),
        )
        team3 = Team(
            id=3, name="Bulls", display_name="Chicago Bulls", is_deleted=True, deleted_at=datetime(2025, 1, 2, 12, 0, 0)
        )

        db_session.add(team1)
        db_session.add(team2)
        db_session.add(team3)
        db_session.commit()

        result = repo.get_deleted_teams()

        assert len(result) == 2

        # Should be ordered by deleted_at desc (most recent first)
        assert result[0].name == "Bulls"  # deleted later
        assert result[1].name == "Lakers"  # deleted earlier

    def test_base_repository_methods(self, db_session):
        """Test inherited base repository methods work correctly."""
        repo = TeamRepository(db_session)

        # Test create
        team = repo.create(name="Hawks", display_name="Atlanta Hawks")
        assert team.name == "Hawks"
        assert team.display_name == "Atlanta Hawks"
        assert team.id is not None

        # Test get_all
        all_teams = repo.get_all()
        assert len(all_teams) == 1
        assert all_teams[0].name == "Hawks"

        # Test get_by_id
        retrieved = repo.get_by_id(team.id)
        assert retrieved is not None
        assert retrieved.name == "Hawks"

        # Test update
        updated = repo.update(team.id, display_name="Atlanta Hawks Updated")
        assert updated.display_name == "Atlanta Hawks Updated"

        # Test soft delete
        result = repo.soft_delete(team.id)
        assert result is True

        # Team should be marked as deleted
        db_session.refresh(team)
        assert team.is_deleted is True
        assert team.deleted_at is not None

    def test_inheritance_from_base_repository(self, db_session):
        """Test that TeamRepository properly inherits from BaseRepository."""
        repo = TeamRepository(db_session)

        # Check that model is set correctly
        assert repo.model == Team

        # Check that session is set
        assert repo.session == db_session
