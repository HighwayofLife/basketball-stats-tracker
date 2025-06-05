"""Tests for stats_aggregator utility."""

from app.utils.stats_aggregator import aggregate_quarter_shot_strings


def test_aggregate_quarter_shot_strings(test_shot_mapping):
    """Aggregates multiple quarter shot strings."""
    quarters, totals = aggregate_quarter_shot_strings(
        ["11", "22-", "3/", ""],
        test_shot_mapping,
    )

    assert len(quarters) == 4
    assert totals == {
        "ftm": 2,
        "fta": 2,
        "fg2m": 2,
        "fg2a": 3,
        "fg3m": 1,
        "fg3a": 2,
    }
