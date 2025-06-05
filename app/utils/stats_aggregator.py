"""Utility for aggregating quarter shot strings into totals."""

from collections.abc import Callable
from typing import Any

from .input_parser import parse_quarter_shot_string


def aggregate_quarter_shot_strings(
    quarter_shot_strings: list[str],
    shot_mapping: dict[str, dict[str, Any]],
    parse_func: Callable[[str, dict[str, dict[str, Any]]], dict[str, int]] | None = None,
) -> tuple[list[dict[str, int]], dict[str, int]]:
    """Parse shot strings for up to four quarters and aggregate totals.

    Args:
        quarter_shot_strings: Shot strings for each quarter. Missing quarters are treated as empty strings.
        shot_mapping: Mapping of shot characters to their type and outcome.
        parse_func: Optional parser function. Defaults to :func:`parse_quarter_shot_string`.

    Returns:
        A tuple ``(quarter_stats, totals)`` where ``quarter_stats`` is a list of
        four dictionaries with per-quarter stats and ``totals`` aggregates all
        quarters.
    """
    parser = parse_func or parse_quarter_shot_string

    quarter_stats: list[dict[str, int]] = []
    totals = {"ftm": 0, "fta": 0, "fg2m": 0, "fg2a": 0, "fg3m": 0, "fg3a": 0}

    for i in range(4):
        shot_string = quarter_shot_strings[i] if i < len(quarter_shot_strings) else ""
        stats = parser(shot_string, shot_mapping)
        quarter_stats.append(stats)
        totals["ftm"] += stats["ftm"]
        totals["fta"] += stats["fta"]
        totals["fg2m"] += stats["fg2m"]
        totals["fg2a"] += stats["fg2a"]
        totals["fg3m"] += stats["fg3m"]
        totals["fg3a"] += stats["fg3a"]

    return quarter_stats, totals
