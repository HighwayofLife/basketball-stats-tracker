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
        """Test unique constraint violation."""
        # Create first award
        create_player_award(
            session=unit_db_session,
            player_id=shared_test_player.id,
            season="2024",
            award_type="player_of_the_week",
            week_date=date(2024, 1, 1),
            points_scored=25,
        )
        unit_db_session.commit()

        # Try to create duplicate (same award_type, week_date, season)
        with pytest.raises(IntegrityError):
            create_player_award(
                session=unit_db_session,
                player_id=shared_test_player.id,
                season="2024",
                award_type="player_of_the_week",
                week_date=date(2024, 1, 1),
                points_scored=30,
            )
            unit_db_session.commit()


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
