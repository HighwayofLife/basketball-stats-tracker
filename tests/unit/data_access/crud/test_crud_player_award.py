"""Unit tests for PlayerAward CRUD operations."""

from datetime import date, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.data_access.crud.crud_player_award import (
    count_awards_for_player,
    create_player_award,
    delete_all_awards_by_type,
    delete_awards_for_week,
    get_all_awards_for_player,
    get_awards_by_week,
    get_comprehensive_player_award_summary,
    get_current_week_awards,
    get_player_award_counts_by_season,
    get_player_awards_by_season,
    get_player_awards_by_type,
    get_recent_awards,
)


class TestCreatePlayerAward:
    """Test player award creation."""

    def test_create_player_award_success(self, unit_db_session, shared_test_player):
        """Test successful player award creation."""
        award = create_player_award(
            session=unit_db_session,
            player_id=shared_test_player.id,
            season="2024",
            award_type="player_of_the_week",
            week_date=date(2024, 1, 1),
            points_scored=25,
        )

        assert award.id is not None
        assert award.player_id == shared_test_player.id
        assert award.season == "2024"
        assert award.award_type == "player_of_the_week"
        assert award.week_date == date(2024, 1, 1)
        assert award.points_scored == 25
        assert isinstance(award.created_at, datetime)

    def test_create_player_award_without_points(self, unit_db_session, shared_test_player):
        """Test creating award without points scored."""
        award = create_player_award(
            session=unit_db_session,
            player_id=shared_test_player.id,
            season="2024",
            award_type="player_of_the_week",
            week_date=date(2024, 1, 8),
        )

        assert award.points_scored is None

    def test_create_player_award_duplicate_constraint(self, unit_db_session, shared_test_player):
        """Test unique constraint violation with non-NULL game_id."""
        # Create first award with specific game_id
        create_player_award(
            session=unit_db_session,
            player_id=shared_test_player.id,
            season="2024",
            award_type="dub_club",
            week_date=date(2024, 1, 1),
            points_scored=25,
            game_id=1,  # Specific game
        )
        unit_db_session.commit()

        # Try to create duplicate (same player_id, award_type, week_date, season, game_id)
        with pytest.raises(IntegrityError):
            create_player_award(
                session=unit_db_session,
                player_id=shared_test_player.id,
                season="2024",
                award_type="dub_club",
                week_date=date(2024, 1, 1),
                points_scored=30,
                game_id=1,  # Same game_id should trigger constraint
            )
            unit_db_session.commit()

    def test_create_player_award_different_game_ids_allowed(self, unit_db_session, shared_test_player):
        """Test that same player can get multiple awards for same week with different game_ids."""
        # Create first award for game 1
        award1 = create_player_award(
            session=unit_db_session,
            player_id=shared_test_player.id,
            season="2024",
            award_type="dub_club",
            week_date=date(2024, 1, 1),
            points_scored=25,
            game_id=1,
        )
        unit_db_session.commit()

        # Create second award for game 2 (should succeed)
        award2 = create_player_award(
            session=unit_db_session,
            player_id=shared_test_player.id,
            season="2024",
            award_type="dub_club",
            week_date=date(2024, 1, 1),
            points_scored=30,
            game_id=2,
        )
        unit_db_session.commit()

        # Both awards should exist
        assert award1.id != award2.id
        assert award1.game_id == 1
        assert award2.game_id == 2

    def test_create_player_award_sqlite_null_behavior(self, unit_db_session, shared_test_player):
        """Test SQLite-specific behavior: NULL values in unique constraints are not considered equal."""
        # Note: This test documents SQLite's behavior which differs from PostgreSQL.
        # In production (PostgreSQL), this would likely fail, but in SQLite it succeeds.

        # Create first award with game_id=None
        award1 = create_player_award(
            session=unit_db_session,
            player_id=shared_test_player.id,
            season="2024",
            award_type="player_of_the_week",
            week_date=date(2024, 1, 1),
            points_scored=25,
            game_id=None,
        )
        unit_db_session.commit()

        # Create second award with game_id=None (SQLite allows this)
        award2 = create_player_award(
            session=unit_db_session,
            player_id=shared_test_player.id,
            season="2024",
            award_type="player_of_the_week",
            week_date=date(2024, 1, 1),
            points_scored=30,
            game_id=None,
        )
        unit_db_session.commit()

        # Both awards should exist in SQLite
        assert award1.id != award2.id
        assert award1.game_id is None
        assert award2.game_id is None


class TestGetPlayerAwards:
    """Test retrieving player awards."""

    def test_get_player_awards_by_season(self, unit_db_session, shared_test_player):
        """Test getting awards for specific season."""
        # Create awards in different seasons
        award1 = create_player_award(
            unit_db_session, shared_test_player.id, "2024", "player_of_the_week", date(2024, 1, 1), 25
        )
        award2 = create_player_award(
            unit_db_session, shared_test_player.id, "2024", "player_of_the_week", date(2024, 1, 8), 30
        )
        create_player_award(unit_db_session, shared_test_player.id, "2025", "player_of_the_week", date(2025, 1, 1), 20)

        awards = get_player_awards_by_season(unit_db_session, shared_test_player.id, "2024")

        assert len(awards) == 2
        # Should be ordered by week_date desc
        assert awards[0].week_date == date(2024, 1, 8)
        assert awards[1].week_date == date(2024, 1, 1)

    def test_get_player_awards_by_type(self, unit_db_session, shared_test_player):
        """Test getting awards by type."""
        create_player_award(unit_db_session, shared_test_player.id, "2024", "player_of_the_week", date(2024, 1, 1), 25)
        create_player_award(unit_db_session, shared_test_player.id, "2024", "mvp", date(2024, 1, 8), 40)

        potw_awards = get_player_awards_by_type(unit_db_session, shared_test_player.id, "player_of_the_week")

        assert len(potw_awards) == 1
        assert potw_awards[0].award_type == "player_of_the_week"

    def test_get_player_award_counts_by_season(self, unit_db_session, shared_test_player):
        """Test getting award counts grouped by season."""
        # Create multiple awards across seasons
        create_player_award(unit_db_session, shared_test_player.id, "2024", "player_of_the_week", date(2024, 1, 1), 25)
        create_player_award(unit_db_session, shared_test_player.id, "2024", "player_of_the_week", date(2024, 1, 8), 30)
        create_player_award(unit_db_session, shared_test_player.id, "2025", "player_of_the_week", date(2025, 1, 1), 20)

        counts = get_player_award_counts_by_season(unit_db_session, shared_test_player.id)

        assert counts["2024"] == 2
        assert counts["2025"] == 1

    def test_get_all_awards_for_player(self, unit_db_session, shared_test_player):
        """Test getting all awards for a player."""
        create_player_award(unit_db_session, shared_test_player.id, "2024", "player_of_the_week", date(2024, 1, 1), 25)
        create_player_award(unit_db_session, shared_test_player.id, "2025", "mvp", date(2025, 1, 1), 40)

        awards = get_all_awards_for_player(unit_db_session, shared_test_player.id)

        assert len(awards) == 2
        # Should be ordered by season desc, week_date desc
        assert awards[0].season == "2025"
        assert awards[1].season == "2024"


class TestDeletePlayerAwards:
    """Test deleting player awards."""

    def test_delete_awards_for_week(self, unit_db_session, shared_test_player):
        """Test deleting awards for specific week."""
        create_player_award(unit_db_session, shared_test_player.id, "2024", "player_of_the_week", date(2024, 1, 1), 25)
        create_player_award(unit_db_session, shared_test_player.id, "2024", "player_of_the_week", date(2024, 1, 8), 30)

        deleted_count = delete_awards_for_week(unit_db_session, "player_of_the_week", date(2024, 1, 1), "2024")

        assert deleted_count == 1

        remaining_awards = get_player_awards_by_season(unit_db_session, shared_test_player.id, "2024")
        assert len(remaining_awards) == 1
        assert remaining_awards[0].week_date == date(2024, 1, 8)

    def test_delete_all_awards_by_type(self, unit_db_session, shared_test_player):
        """Test deleting all awards of specific type."""
        create_player_award(unit_db_session, shared_test_player.id, "2024", "player_of_the_week", date(2024, 1, 1), 25)
        create_player_award(unit_db_session, shared_test_player.id, "2024", "player_of_the_week", date(2024, 1, 8), 30)
        create_player_award(unit_db_session, shared_test_player.id, "2024", "mvp", date(2024, 1, 15), 40)

        deleted_count = delete_all_awards_by_type(unit_db_session, "player_of_the_week")

        assert deleted_count == 2

        remaining_awards = get_all_awards_for_player(unit_db_session, shared_test_player.id)
        assert len(remaining_awards) == 1
        assert remaining_awards[0].award_type == "mvp"

    def test_get_awards_by_week(self, unit_db_session, shared_test_player):
        """Test getting awards for specific week."""
        create_player_award(unit_db_session, shared_test_player.id, "2024", "player_of_the_week", date(2024, 1, 1), 25)

        awards = get_awards_by_week(unit_db_session, "player_of_the_week", date(2024, 1, 1), "2024")

        assert len(awards) == 1
        assert awards[0].week_date == date(2024, 1, 1)


class TestAwardUtilities:
    """Test utility functions for awards."""

    def test_get_recent_awards(self, unit_db_session, shared_test_player):
        """Test getting recent awards."""
        # Create awards with different creation times
        for i in range(5):
            create_player_award(
                unit_db_session, shared_test_player.id, "2024", "player_of_the_week", date(2024, 1, 1 + i * 7), 25 + i
            )

        recent_awards = get_recent_awards(unit_db_session, "player_of_the_week", limit=3)

        assert len(recent_awards) == 3
        # Should be ordered by created_at desc

    def test_count_awards_for_player(self, unit_db_session, shared_test_player):
        """Test counting awards for player."""
        create_player_award(unit_db_session, shared_test_player.id, "2024", "player_of_the_week", date(2024, 1, 1), 25)
        create_player_award(unit_db_session, shared_test_player.id, "2024", "mvp", date(2024, 1, 8), 40)

        total_count = count_awards_for_player(unit_db_session, shared_test_player.id)
        potw_count = count_awards_for_player(unit_db_session, shared_test_player.id, "player_of_the_week")

        assert total_count == 2
        assert potw_count == 1

    def test_empty_results(self, unit_db_session, shared_test_player):
        """Test functions return empty results when no awards exist."""
        awards = get_player_awards_by_season(unit_db_session, shared_test_player.id, "2024")
        counts = get_player_award_counts_by_season(unit_db_session, shared_test_player.id)

        assert len(awards) == 0
        assert len(counts) == 0


class TestComprehensiveAwardSummary:
    """Test comprehensive award summary function."""

    def test_get_comprehensive_player_award_summary_with_awards(self, unit_db_session, shared_test_player):
        """Test comprehensive summary with both weekly and season awards."""
        # Create weekly awards
        create_player_award(unit_db_session, shared_test_player.id, "2024", "player_of_the_week", date(2024, 1, 1), 25)
        create_player_award(
            unit_db_session, shared_test_player.id, "2024", "quarterly_firepower", date(2024, 1, 8), None
        )

        # Create season award (week_date is None)
        create_player_award(unit_db_session, shared_test_player.id, "2024", "top_scorer", None, None)

        summary = get_comprehensive_player_award_summary(unit_db_session, shared_test_player.id)

        # Check structure
        assert "weekly_awards" in summary
        assert "season_awards" in summary
        assert "current_season" in summary

        # Check weekly awards
        weekly = summary["weekly_awards"]
        assert "player_of_the_week" in weekly
        assert "quarterly_firepower" in weekly
        assert weekly["player_of_the_week"]["total_count"] == 1
        assert weekly["quarterly_firepower"]["total_count"] == 1

        # Check season awards
        season = summary["season_awards"]
        assert "2024" in season
        assert "top_scorer" in season["2024"]

    def test_get_comprehensive_player_award_summary_no_awards(self, unit_db_session, shared_test_player):
        """Test comprehensive summary with no awards."""
        summary = get_comprehensive_player_award_summary(unit_db_session, shared_test_player.id)

        assert summary["weekly_awards"] == {}
        assert summary["season_awards"] == {}
        assert "current_season" in summary


class TestCurrentWeekAwards:
    """Test current week awards function."""

    def test_get_current_week_awards_with_awards(self, unit_db_session, shared_test_player):
        """Test getting current week awards when awards exist."""
        from datetime import datetime, timedelta

        # Calculate current week Monday
        today = datetime.now().date()
        days_since_monday = today.weekday()
        current_week_monday = today - timedelta(days=days_since_monday)
        current_year = str(today.year)

        # Merge the test player into this session (handles cross-session object)
        merged_player = unit_db_session.merge(shared_test_player)
        unit_db_session.flush()  # Flush to ensure the player is persisted

        # Create awards for current week for the merged player
        create_player_award(
            unit_db_session, merged_player.id, current_year, "player_of_the_week", current_week_monday, 25
        )
        create_player_award(
            unit_db_session, merged_player.id, current_year, "quarterly_firepower", current_week_monday, None
        )

        # Commit everything to the database
        unit_db_session.commit()

        awards = get_current_week_awards(unit_db_session)

        # Check structure
        assert "current_week" in awards
        assert "awards" in awards
        assert "total_awards" in awards

        # Check data
        assert awards["current_week"] == current_week_monday.isoformat()
        assert awards["total_awards"] == 2
        assert "player_of_the_week" in awards["awards"]
        assert "quarterly_firepower" in awards["awards"]

        # Check player data - same player won both awards
        potw_winners = awards["awards"]["player_of_the_week"]
        assert len(potw_winners) == 1
        assert potw_winners[0]["player_id"] == merged_player.id
        assert potw_winners[0]["points_scored"] == 25

        firepower_winners = awards["awards"]["quarterly_firepower"]
        assert len(firepower_winners) == 1
        assert firepower_winners[0]["player_id"] == merged_player.id

    def test_get_current_week_awards_no_awards(self, unit_db_session):
        """Test getting current week awards when no awards exist."""
        awards = get_current_week_awards(unit_db_session)

        assert awards["total_awards"] == 0
        assert awards["awards"] == {}
        assert "current_week" in awards
