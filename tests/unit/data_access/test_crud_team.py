"""
Test module for team CRUD operations.
"""

import pytest
from sqlalchemy.exc import IntegrityError

from app.data_access.crud.crud_team import create_team, get_all_teams, get_team_by_id, get_team_by_name, update_team
from app.data_access.models import Team


class TestTeamCrud:
    """Tests for Team CRUD operations."""

    def test_create_team(self, db_session):
        """Test creating a team."""
        team = create_team(db_session, "Test Team")

        assert isinstance(team, Team)
        assert team.id is not None
        assert team.name == "Test Team"
        assert team.display_name == "Test Team"  # Should default to name

    def test_create_team_with_display_name(self, db_session):
        """Test creating a team with a custom display name."""
        team = create_team(db_session, "Red", "Red Dragons")

        assert isinstance(team, Team)
        assert team.id is not None
        assert team.name == "Red"
        assert team.display_name == "Red Dragons"

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

    def test_update_team_display_name(self, db_session):
        """Test updating a team's display name."""
        # Create a team
        team = create_team(db_session, "Blue", "Blue Team")
        original_id = team.id

        # Update the display name
        updated_team = update_team(db_session, original_id, display_name="Blue Knights")

        assert updated_team is not None
        assert updated_team.id == original_id
        assert updated_team.name == "Blue"  # Name should not change
        assert updated_team.display_name == "Blue Knights"

    def test_update_team_name_and_display_name(self, db_session):
        """Test updating both name and display name."""
        # Create a team
        team = create_team(db_session, "Green")
        original_id = team.id

        # Update both name and display name
        updated_team = update_team(db_session, original_id, name="Green Team", display_name="Green Machine")

        assert updated_team is not None
        assert updated_team.id == original_id
        assert updated_team.name == "Green Team"
        assert updated_team.display_name == "Green Machine"

    def test_update_nonexistent_team(self, db_session):
        """Test updating a team that doesn't exist."""
        updated_team = update_team(db_session, 9999, display_name="Should Not Work")
        assert updated_team is None

    def test_team_str_method(self, db_session):
        """Test the Team __str__ method returns display_name when set."""
        # Test with display_name
        team1 = create_team(db_session, "Red", "Red Dragons")
        assert str(team1) == "Red Dragons"

        # Test without display_name (should fall back to name)
        team2 = create_team(db_session, "Blue")
        assert str(team2) == "Blue"
