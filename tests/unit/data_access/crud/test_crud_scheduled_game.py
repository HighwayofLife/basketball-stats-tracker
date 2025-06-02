"""Unit tests for CRUDScheduledGame."""

from datetime import date, time

from app.data_access.crud.crud_scheduled_game import crud_scheduled_game
from app.data_access.models import ScheduledGame, ScheduledGameStatus, Team


class TestCRUDScheduledGame:
    """Test cases for CRUDScheduledGame."""

    def test_create_scheduled_game(self, test_db_file_session):
        """Test creating a scheduled game."""
        # Create teams first
        home_team = Team(name="Home Team")
        away_team = Team(name="Away Team")
        test_db_file_session.add(home_team)
        test_db_file_session.add(away_team)
        test_db_file_session.commit()

        # Create scheduled game
        scheduled_game = crud_scheduled_game.create(
            test_db_file_session,
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            scheduled_date=date(2025, 6, 15),
            scheduled_time="19:30",
            location="Test Arena",
            notes="Test game",
        )

        # Assert
        assert scheduled_game.id is not None
        assert scheduled_game.scheduled_date == date(2025, 6, 15)
        assert scheduled_game.scheduled_time == time(19, 30)
        assert scheduled_game.home_team_id == home_team.id
        assert scheduled_game.away_team_id == away_team.id
        assert scheduled_game.location == "Test Arena"
        assert scheduled_game.notes == "Test game"
        assert scheduled_game.status == ScheduledGameStatus.SCHEDULED
        assert scheduled_game.game_id is None

    def test_find_matching_game(self, test_db_file_session):
        """Test finding a scheduled game by date and teams."""
        # Create teams
        team1 = Team(name="Team 1")
        team2 = Team(name="Team 2")
        test_db_file_session.add(team1)
        test_db_file_session.add(team2)
        test_db_file_session.commit()

        # Create scheduled games
        game_date = date(2025, 6, 15)

        scheduled_game1 = ScheduledGame(
            scheduled_date=game_date, home_team_id=team1.id, away_team_id=team2.id, status=ScheduledGameStatus.SCHEDULED
        )
        scheduled_game2 = ScheduledGame(
            scheduled_date=date(2025, 6, 20),  # Different date
            home_team_id=team1.id,
            away_team_id=team2.id,
            status=ScheduledGameStatus.SCHEDULED,
        )
        scheduled_game3 = ScheduledGame(
            scheduled_date=game_date,
            home_team_id=team2.id,  # Teams reversed
            away_team_id=team1.id,
            status=ScheduledGameStatus.SCHEDULED,
        )

        test_db_file_session.add_all([scheduled_game1, scheduled_game2, scheduled_game3])
        test_db_file_session.commit()

        # Test finding exact match
        result = crud_scheduled_game.find_matching_game(test_db_file_session, game_date, "Team 1", "Team 2")
        assert result is not None
        assert result.id == scheduled_game1.id

        # Test with reversed teams (should find either match)
        result = crud_scheduled_game.find_matching_game(test_db_file_session, game_date, "Team 2", "Team 1")
        assert result is not None
        assert result.id in [scheduled_game1.id, scheduled_game3.id]

        # Test with non-existent date
        result = crud_scheduled_game.find_matching_game(test_db_file_session, date(2025, 7, 1), "Team 1", "Team 2")
        assert result is None

    def test_mark_completed(self, test_db_file_session):
        """Test marking a scheduled game as completed."""
        # Create teams and scheduled game
        home_team = Team(name="Home Team")
        away_team = Team(name="Away Team")
        test_db_file_session.add(home_team)
        test_db_file_session.add(away_team)
        test_db_file_session.commit()

        scheduled_game = ScheduledGame(
            scheduled_date=date(2025, 6, 15),
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            status=ScheduledGameStatus.SCHEDULED,
        )
        test_db_file_session.add(scheduled_game)
        test_db_file_session.commit()

        # Mark as completed
        actual_game_id = 100
        updated_game = crud_scheduled_game.mark_completed(test_db_file_session, scheduled_game.id, actual_game_id)

        # Assert
        assert updated_game.status == ScheduledGameStatus.COMPLETED
        assert updated_game.game_id == actual_game_id

        # Verify in database
        test_db_file_session.refresh(scheduled_game)
        assert scheduled_game.status == ScheduledGameStatus.COMPLETED
        assert scheduled_game.game_id == actual_game_id

    def test_get_upcoming(self, test_db_file_session):
        """Test getting upcoming scheduled games."""
        # Create teams
        team1 = Team(name="Team 1")
        team2 = Team(name="Team 2")
        test_db_file_session.add(team1)
        test_db_file_session.add(team2)
        test_db_file_session.commit()

        # Create scheduled games with different dates and statuses
        today = date.today()

        upcoming_game1 = ScheduledGame(
            scheduled_date=today, home_team_id=team1.id, away_team_id=team2.id, status=ScheduledGameStatus.SCHEDULED
        )
        upcoming_game2 = ScheduledGame(
            scheduled_date=date(today.year, today.month, today.day + 5)
            if today.day <= 25
            else date(today.year, today.month + 1, 5),
            home_team_id=team2.id,
            away_team_id=team1.id,
            status=ScheduledGameStatus.SCHEDULED,
        )
        past_game = ScheduledGame(
            scheduled_date=date(today.year, today.month, today.day - 5)
            if today.day > 5
            else date(today.year, today.month - 1, 25),
            home_team_id=team1.id,
            away_team_id=team2.id,
            status=ScheduledGameStatus.SCHEDULED,
        )
        completed_game = ScheduledGame(
            scheduled_date=date(today.year, today.month, today.day + 3)
            if today.day <= 27
            else date(today.year, today.month + 1, 3),
            home_team_id=team1.id,
            away_team_id=team2.id,
            status=ScheduledGameStatus.COMPLETED,
        )

        test_db_file_session.add_all([upcoming_game1, upcoming_game2, past_game, completed_game])
        test_db_file_session.commit()

        # Get upcoming games
        result = crud_scheduled_game.get_upcoming(test_db_file_session)

        # Should include today's game and future scheduled game, but not past or completed
        assert len(result) == 2
        assert all(game.scheduled_date >= today for game in result)
        assert all(game.status == ScheduledGameStatus.SCHEDULED for game in result)

        # Test with limit
        result = crud_scheduled_game.get_upcoming(test_db_file_session, limit=1)
        assert len(result) == 1

    def test_cancel(self, test_db_file_session):
        """Test canceling a scheduled game."""
        # Create teams and scheduled game
        home_team = Team(name="Home Team")
        away_team = Team(name="Away Team")
        test_db_file_session.add(home_team)
        test_db_file_session.add(away_team)
        test_db_file_session.commit()

        scheduled_game = ScheduledGame(
            scheduled_date=date(2025, 6, 15),
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            status=ScheduledGameStatus.SCHEDULED,
            notes="Original notes",
        )
        test_db_file_session.add(scheduled_game)
        test_db_file_session.commit()

        # Cancel the game
        cancelled_game = crud_scheduled_game.cancel(test_db_file_session, scheduled_game.id)

        # Assert
        assert cancelled_game.status == ScheduledGameStatus.CANCELLED

    def test_get_by_status(self, test_db_file_session):
        """Test getting scheduled games by status."""
        # Create teams
        team1 = Team(name="Team 1")
        team2 = Team(name="Team 2")
        test_db_file_session.add(team1)
        test_db_file_session.add(team2)
        test_db_file_session.commit()

        # Create games with different statuses
        scheduled_game = ScheduledGame(
            scheduled_date=date(2025, 6, 15),
            home_team_id=team1.id,
            away_team_id=team2.id,
            status=ScheduledGameStatus.SCHEDULED,
        )
        postponed_game = ScheduledGame(
            scheduled_date=date(2025, 6, 20),
            home_team_id=team2.id,
            away_team_id=team1.id,
            status=ScheduledGameStatus.POSTPONED,
        )
        completed_game = ScheduledGame(
            scheduled_date=date(2025, 6, 10),
            home_team_id=team1.id,
            away_team_id=team2.id,
            status=ScheduledGameStatus.COMPLETED,
        )

        test_db_file_session.add_all([scheduled_game, postponed_game, completed_game])
        test_db_file_session.commit()

        # Test getting by status
        scheduled_games = crud_scheduled_game.get_by_status(test_db_file_session, ScheduledGameStatus.SCHEDULED)
        assert len(scheduled_games) == 1
        assert scheduled_games[0].id == scheduled_game.id

        postponed_games = crud_scheduled_game.get_by_status(test_db_file_session, ScheduledGameStatus.POSTPONED)
        assert len(postponed_games) == 1
        assert postponed_games[0].id == postponed_game.id

    def test_get_by_id(self, test_db_file_session):
        """Test getting a scheduled game by ID."""
        # Create teams and game
        home_team = Team(name="Home Team")
        away_team = Team(name="Away Team")
        test_db_file_session.add(home_team)
        test_db_file_session.add(away_team)
        test_db_file_session.commit()

        scheduled_game = ScheduledGame(
            scheduled_date=date(2025, 6, 15),
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            status=ScheduledGameStatus.SCHEDULED,
        )
        test_db_file_session.add(scheduled_game)
        test_db_file_session.commit()

        # Get by ID
        result = crud_scheduled_game.get_by_id(test_db_file_session, scheduled_game.id)

        assert result is not None
        assert result.id == scheduled_game.id
        assert result.home_team_id == home_team.id
        assert result.away_team_id == away_team.id

        # Test non-existent ID
        result = crud_scheduled_game.get_by_id(test_db_file_session, 9999)
        assert result is None

    def test_update(self, test_db_file_session):
        """Test updating a scheduled game."""
        # Create teams and game
        team1 = Team(name="Team 1")
        team2 = Team(name="Team 2")
        team3 = Team(name="Team 3")
        test_db_file_session.add_all([team1, team2, team3])
        test_db_file_session.commit()

        scheduled_game = ScheduledGame(
            scheduled_date=date(2025, 6, 15),
            home_team_id=team1.id,
            away_team_id=team2.id,
            scheduled_time=time(19, 30),
            location="Old Arena",
            status=ScheduledGameStatus.SCHEDULED,
        )
        test_db_file_session.add(scheduled_game)
        test_db_file_session.commit()

        # Update the game
        updated_game = crud_scheduled_game.update(
            test_db_file_session,
            scheduled_game.id,
            scheduled_date=date(2025, 6, 20),
            scheduled_time="20:00",
            away_team_id=team3.id,
            location="New Arena",
        )

        # Assert
        assert updated_game.scheduled_date == date(2025, 6, 20)
        assert updated_game.scheduled_time == time(20, 0)
        assert updated_game.away_team_id == team3.id
        assert updated_game.location == "New Arena"
        assert updated_game.home_team_id == team1.id  # Unchanged

    def test_delete(self, test_db_file_session):
        """Test soft deleting a scheduled game."""
        # Create teams and game
        home_team = Team(name="Home Team")
        away_team = Team(name="Away Team")
        test_db_file_session.add(home_team)
        test_db_file_session.add(away_team)
        test_db_file_session.commit()

        scheduled_game = ScheduledGame(
            scheduled_date=date(2025, 6, 15),
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            status=ScheduledGameStatus.SCHEDULED,
        )
        test_db_file_session.add(scheduled_game)
        test_db_file_session.commit()

        # Delete the game
        result = crud_scheduled_game.delete(test_db_file_session, scheduled_game.id)

        assert result is True

        # Verify soft delete
        test_db_file_session.refresh(scheduled_game)
        assert scheduled_game.is_deleted is True
        assert scheduled_game.deleted_at is not None

        # Verify it's not returned by get_by_id
        result = crud_scheduled_game.get_by_id(test_db_file_session, scheduled_game.id)
        assert result is None
