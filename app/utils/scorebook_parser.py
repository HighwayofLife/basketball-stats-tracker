"""
Utility module for parsing scorebook notation into basketball statistics.
"""

from typing import Any


def parse_scoring_notation(notation: str) -> dict[str, int]:
    """
    Parse scoring notation string into basketball statistics.

    Args:
        notation: String containing scoring notation using:
            - '1' = Made free throw
            - 'x' = Missed free throw
            - '2' = Made 2-point shot
            - '-' = Missed 2-point shot
            - '3' = Made 3-point shot
            - '/' = Missed 3-point shot

    Returns:
        Dictionary with keys: ftm, fta, fg2m, fg2a, fg3m, fg3a

    Examples:
        >>> parse_scoring_notation("22-1x")
        {'ftm': 1, 'fta': 2, 'fg2m': 2, 'fg2a': 3, 'fg3m': 0, 'fg3a': 0}

        >>> parse_scoring_notation("3/2")
        {'ftm': 0, 'fta': 0, 'fg2m': 1, 'fg2a': 1, 'fg3m': 1, 'fg3a': 2}
    """
    if not notation:
        return {"ftm": 0, "fta": 0, "fg2m": 0, "fg2a": 0, "fg3m": 0, "fg3a": 0}

    # Initialize stats
    stats = {
        "ftm": 0,  # Free throws made
        "fta": 0,  # Free throws attempted
        "fg2m": 0,  # 2-point field goals made
        "fg2a": 0,  # 2-point field goals attempted
        "fg3m": 0,  # 3-point field goals made
        "fg3a": 0,  # 3-point field goals attempted
    }

    # Parse each character in the notation
    for char in notation.lower():
        if char == "1":
            # Made free throw
            stats["ftm"] += 1
            stats["fta"] += 1
        elif char == "x":
            # Missed free throw
            stats["fta"] += 1
        elif char == "2":
            # Made 2-point shot
            stats["fg2m"] += 1
            stats["fg2a"] += 1
        elif char == "-":
            # Missed 2-point shot
            stats["fg2a"] += 1
        elif char == "3":
            # Made 3-point shot
            stats["fg3m"] += 1
            stats["fg3a"] += 1
        elif char == "/":
            # Missed 3-point shot
            stats["fg3a"] += 1
        # Ignore any other characters (spaces, etc.)

    return stats


def calculate_points_from_notation(notation: str) -> int:
    """
    Calculate total points scored from scoring notation.

    Args:
        notation: String containing scoring notation

    Returns:
        Total points scored

    Examples:
        >>> calculate_points_from_notation("22-1x")
        5

        >>> calculate_points_from_notation("3/2")
        5
    """
    if not notation:
        return 0

    points = 0
    for char in notation.lower():
        if char == "1":
            points += 1  # Free throw
        elif char == "2":
            points += 2  # 2-point shot
        elif char == "3":
            points += 3  # 3-point shot
        # Misses don't add points

    return points


def validate_scoring_notation(notation: str) -> tuple[bool, str]:
    """
    Validate that scoring notation contains only valid characters.

    Args:
        notation: String to validate

    Returns:
        Tuple of (is_valid, error_message)

    Examples:
        >>> validate_scoring_notation("22-1x")
        (True, "")

        >>> validate_scoring_notation("22-1z")
        (False, "Invalid character 'z' in scoring notation")
    """
    if not notation:
        return True, ""

    valid_chars = {"1", "x", "2", "-", "3", "/", " ", "\t"}

    for char in notation.lower():
        if char not in valid_chars:
            return False, f"Invalid character '{char}' in scoring notation"

    return True, ""


def parse_scorebook_entry(player_data: dict[str, Any]) -> dict[str, Any]:
    """
    Parse a complete scorebook entry for a player into game statistics.

    Args:
        player_data: Dictionary containing:
            - player_id: Player ID
            - fouls: Number of fouls
            - qt1_shots, qt2_shots, qt3_shots, qt4_shots: Scoring notation for each quarter

    Returns:
        Dictionary containing parsed game and quarter statistics

    Raises:
        ValueError: If scoring notation is invalid
    """
    # Validate required fields
    if "player_id" not in player_data:
        raise ValueError("player_id is required")

    if "fouls" not in player_data:
        raise ValueError("fouls is required")

    # Initialize result
    result = {
        "player_id": player_data["player_id"],
        "fouls": int(player_data.get("fouls", 0)),
        "total_stats": {"ftm": 0, "fta": 0, "fg2m": 0, "fg2a": 0, "fg3m": 0, "fg3a": 0},
        "quarter_stats": [],
    }

    # Process each quarter (Q1-Q4 and OT1-OT2)
    quarter_mappings = {1: "qt1_shots", 2: "qt2_shots", 3: "qt3_shots", 4: "qt4_shots", 5: "ot1_shots", 6: "ot2_shots"}

    for quarter in range(1, 7):
        quarter_key = quarter_mappings.get(quarter, f"qt{quarter}_shots")
        notation = player_data.get(quarter_key, "")

        # Validate notation
        is_valid, error_msg = validate_scoring_notation(notation)
        if not is_valid:
            raise ValueError(f"Quarter {quarter}: {error_msg}")

        # Parse quarter stats
        quarter_stats = parse_scoring_notation(notation)
        quarter_stats["quarter_number"] = quarter
        result["quarter_stats"].append(quarter_stats)

        # Add to total stats
        for key in ["ftm", "fta", "fg2m", "fg2a", "fg3m", "fg3a"]:
            result["total_stats"][key] += quarter_stats[key]

    return result


def format_scoring_notation_help() -> dict[str, Any]:
    """
    Return help text for scoring notation.

    Returns:
        Dictionary with notation explanations
    """
    return {
        "free_throws": {"1": "Made free throw", "x": "Missed free throw"},
        "two_points": {"2": "Made 2-point shot", "-": "Missed 2-point shot"},
        "three_points": {"3": "Made 3-point shot", "/": "Missed 3-point shot"},
        "examples": {
            "22-1x": "2 made 2pts, 1 missed 2pt, 1 made FT, 1 missed FT (5 points)",
            "3/2": "1 made 3pt, 1 missed 3pt, 1 made 2pt (5 points)",
            "11": "2 made free throws (2 points)",
            "-/": "1 missed 2pt, 1 missed 3pt (0 points)",
            "321": "1 made 3pt, 1 made 2pt, 1 made FT (6 points)",
        },
    }


def calculate_team_score_from_players(players_data: list[dict[str, Any]]) -> int:
    """
    Calculate total team score from multiple player scorebook entries.

    Args:
        players_data: List of player data dictionaries

    Returns:
        Total team score
    """
    total_score = 0

    for player_data in players_data:
        for quarter in range(1, 5):
            quarter_key = f"qt{quarter}_shots"
            notation = player_data.get(quarter_key, "")
            total_score += calculate_points_from_notation(notation)

    return total_score


def get_shooting_percentages(stats: dict[str, int]) -> dict[str, float]:
    """
    Calculate shooting percentages from stats.

    Args:
        stats: Dictionary with shooting stats (ftm, fta, fg2m, fg2a, fg3m, fg3a)

    Returns:
        Dictionary with calculated percentages
    """
    percentages = {}

    # Free throw percentage
    if stats.get("fta", 0) > 0:
        percentages["ft_pct"] = round(stats["ftm"] / stats["fta"] * 100, 1)
    else:
        percentages["ft_pct"] = 0.0

    # 2-point percentage
    if stats.get("fg2a", 0) > 0:
        percentages["fg2_pct"] = round(stats["fg2m"] / stats["fg2a"] * 100, 1)
    else:
        percentages["fg2_pct"] = 0.0

    # 3-point percentage
    if stats.get("fg3a", 0) > 0:
        percentages["fg3_pct"] = round(stats["fg3m"] / stats["fg3a"] * 100, 1)
    else:
        percentages["fg3_pct"] = 0.0

    # Overall field goal percentage
    total_fgm = stats.get("fg2m", 0) + stats.get("fg3m", 0)
    total_fga = stats.get("fg2a", 0) + stats.get("fg3a", 0)

    if total_fga > 0:
        percentages["fg_pct"] = round(total_fgm / total_fga * 100, 1)
    else:
        percentages["fg_pct"] = 0.0

    return percentages
