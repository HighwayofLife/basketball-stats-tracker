# app/config/awards.py

"""
Centralized award configuration for the Basketball Stats Tracker.

This module contains all award definitions including names, icons, descriptions,
and formatting rules in one place to maintain consistency across the application.
"""

from typing import Any

# Weekly Award Configuration
WEEKLY_AWARDS = {
    "player_of_the_week": {
        "name": "The Offensive Onslaught",
        "icon": "🏀",
        "desc": "Best single-game scoring performance (FG% tie-breaker)",
        "format_stat": None,  # Uses points_scored instead
        "format_points": True,
    },
    "quarterly_firepower": {
        "name": "Quarter Pounder",
        "icon": "🔥",
        "desc": "Highest points in any single quarter",
        "format_stat": "pts",
        "format_points": False,
    },
    "weekly_ft_king": {
        "name": "Freethrow Merchant",
        "icon": "👑",
        "desc": "Most free throws made in a single game",
        "format_stat": "FTM",
        "format_points": False,
    },
    "hot_hand_weekly": {
        "name": "The Human Cheat Code",
        "icon": "🎯",
        "desc": "Highest FG% in a single game (minimum 10 attempts)",
        "format_stat": "percentage",
        "format_points": False,
    },
    "clutch_man": {
        "name": "The Final Boss",
        "icon": "⏰",
        "desc": "Most shots made in 4th quarter of a single game",
        "format_stat": "Q4 makes",
        "format_points": False,
    },
    "trigger_finger": {
        "name": "Trigger Finger",
        "icon": "🎪",
        "desc": "Most shot attempts in a single game",
        "format_stat": "attempts",
        "format_points": False,
    },
    "weekly_whiffer": {
        "name": "Weekly Whiffer",
        "icon": "😅",
        "desc": "Most missed shots in a single game",
        "format_stat": "misses",
        "format_points": False,
    },
    "human_howitzer": {
        "name": "Human Howitzer",
        "icon": "🚀",
        "desc": "Most 3-point shots made in a single game",
        "format_stat": "3PM",
        "format_points": False,
    },
    "dub_club": {
        "name": "Dub Club",
        "icon": "🎖️",
        "desc": "Scored 20 or more points in a single game",
        "format_stat": None,
        "format_points": True,
    },
}

# Season Award Configuration
SEASON_AWARDS = {
    "top_scorer": {
        "name": "Top Scorer",
        "icon": "🥇",
        "desc": "Most total points scored in the season",
    },
    "sharpshooter": {
        "name": "Sharpshooter",
        "icon": "🎯",
        "desc": "Highest 3-point percentage with dynamic minimum attempts",
    },
    "efficiency_expert": {
        "name": "Efficiency Expert",
        "icon": "📈",
        "desc": "Highest field goal percentage with dynamic minimum attempts",
    },
    "charity_stripe_regular": {
        "name": "Charity Stripe Regular",
        "icon": "🎰",
        "desc": "Most free throw attempts in the season",
    },
    "human_highlight_reel": {
        "name": "Human Highlight Reel",
        "icon": "🎬",
        "desc": "Most combined made shots (2pt + 3pt + FT) in the season",
    },
    "defensive_tackle": {
        "name": "Defensive Tackle",
        "icon": "🛡️",
        "desc": "Most fouls committed in the season",
    },
    "air_ball_artist": {
        "name": "Air Ball Artist",
        "icon": "🎨",
        "desc": "Most 3-point misses in the season",
    },
    "air_assault": {
        "name": "Air Assault",
        "icon": "⚔️",
        "desc": "Most total shot attempts in the season",
    },
}

# Combined awards dictionary for convenience
ALL_AWARDS = {**WEEKLY_AWARDS, **SEASON_AWARDS}


def get_award_info(award_type: str) -> dict[str, Any]:
    """
    Get award information for a given award type.

    Args:
        award_type: The award type key (e.g., 'player_of_the_week')

    Returns:
        Dictionary containing award name, icon, description, and formatting info.
        Returns fallback info if award type not found.
    """
    return ALL_AWARDS.get(
        award_type,
        {
            "name": award_type.replace("_", " ").title(),
            "icon": "🏆",
            "desc": "Award description",
            "format_stat": None,
            "format_points": False,
        },
    )


def get_weekly_award_info(award_type: str) -> dict[str, Any]:
    """Get award information for weekly awards specifically."""
    return WEEKLY_AWARDS.get(award_type, get_award_info(award_type))


def get_season_award_info(award_type: str) -> dict[str, Any]:
    """Get award information for season awards specifically."""
    return SEASON_AWARDS.get(award_type, get_award_info(award_type))


def format_award_stat(award_type: str, stat_value: float) -> str:
    """
    Format award stat value according to the award's formatting rules.

    Args:
        award_type: The award type key
        stat_value: The raw stat value to format

    Returns:
        Formatted string representation of the stat
    """
    info = get_award_info(award_type)

    if not info.get("format_stat"):
        return ""

    if info["format_stat"] == "percentage":
        return f"{stat_value * 100:.1f}% FG"
    else:
        # Format as integer for counts (shots made, points, attempts, etc.)
        return f"{int(stat_value)} {info['format_stat']}"


def get_award_display_data(award_type: str, stat_value: float = None, points_scored: int = None) -> dict[str, Any]:
    """
    Get complete display data for an award including formatted stats.

    Args:
        award_type: The award type key
        stat_value: The raw stat value (optional)
        points_scored: Points scored for the award (optional)

    Returns:
        Complete display data dictionary
    """
    info = get_award_info(award_type)

    result = {
        "award_name": info["name"],
        "award_icon": info["icon"],
        "award_desc": info["desc"],
        "show_points": info.get("format_points", False) and points_scored is not None,
        "points_scored": points_scored,
        "formatted_stat": None,
    }

    if stat_value is not None and info.get("format_stat"):
        result["formatted_stat"] = format_award_stat(award_type, stat_value)

    return result
