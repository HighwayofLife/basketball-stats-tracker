"""
Test module for team CRUD operations.
"""

import pytest
from sqlalchemy.exc import IntegrityError

from app.data_access.crud.crud_team import create_team, get_all_teams, get_team_by_id, get_team_by_name
from app.data_access.models import Team


class TestTeamCrud:
    """Tests for Team CRUD operations."""

    def test_create_team(self, db_session):
        """Test creating a team."""
        team = create_team(db_session, "Test Team")

        assert isinstance(team, Team)
        assert team.id is not None
        assert team.name == "Test Team"

    def test_create_duplicate_team(self, db_session):
        """Test that creating a team with the same name raises an IntegrityError."""
        # Create the first team
        team1 = create_team(db_session, "Duplicate Team")
        assert team1.name == "Duplicate Team"

        # Try to create a second team with the same name
        with pytest.raises(IntegrityError):
            create_team(db_session, "Duplicate Team")

    def test_get_team_by_name(self, db_session):
        """Test getting a team by name."""
        original_team = create_team(db_session, "Named Team")

        # Get the team by name
        retrieved_team = get_team_by_name(db_session, "Named Team")

        assert retrieved_team is not None
        assert retrieved_team.id == original_team.id
        assert retrieved_team.name == "Named Team"

    def test_get_team_by_name_not_found(self, db_session):
        """Test getting a team by name that doesn't exist."""
        retrieved_team = get_team_by_name(db_session, "Nonexistent Team")
        assert retrieved_team is None

    def test_get_team_by_id(self, db_session):
        """Test getting a team by ID."""
        original_team = create_team(db_session, "ID Team")

        # Get the team by ID
        retrieved_team = get_team_by_id(db_session, original_team.id)

        assert retrieved_team is not None
        assert retrieved_team.id == original_team.id
        assert retrieved_team.name == "ID Team"

    def test_get_team_by_id_not_found(self, db_session):
        """Test getting a team by ID that doesn't exist."""
        retrieved_team = get_team_by_id(db_session, 9999)  # Assuming ID 9999 doesn't exist
        assert retrieved_team is None

    def test_get_all_teams_empty(self, db_session):
        """Test getting all teams when there are none."""
        teams = get_all_teams(db_session)
        assert isinstance(teams, list)
        assert len(teams) == 0

    def test_get_all_teams(self, db_session):
        """Test getting all teams."""
        # Create some teams
        team1 = create_team(db_session, "Team 1")
        team2 = create_team(db_session, "Team 2")
        team3 = create_team(db_session, "Team 3")

        # Get all teams
        teams = get_all_teams(db_session)

        assert isinstance(teams, list)
        assert len(teams) == 3
        assert any(t.id == team1.id for t in teams)
        assert any(t.id == team2.id for t in teams)
        assert any(t.id == team3.id for t in teams)
