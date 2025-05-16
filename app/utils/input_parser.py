"""
Utility for parsing shot strings from game statistics input.
"""

from typing import Any


def parse_quarter_shot_string(shot_string: str, shot_mapping: dict[str, dict[str, Any]]) -> dict[str, int]:
    """
    Parse a quarter shot string into a dictionary with counts of makes and attempts for each shot type.

    Args:
        shot_string: The string representing shots taken in a quarter, e.g., "22-1x/".
        shot_mapping: A dictionary mapping shot characters to their properties (type, made, points).

    Returns:
        A dictionary with counts for:
            - ftm (Free Throws Made)
            - fta (Free Throws Attempted)
            - fg2m (2-Point Field Goals Made)
            - fg2a (2-Point Field Goals Attempted)
            - fg3m (3-Point Field Goals Made)
            - fg3a (3-Point Field Goals Attempted)

    Example:
        >>> parse_quarter_shot_string("22-1x/", SHOT_MAPPING)
        {'ftm': 1, 'fta': 2, 'fg2m': 2, 'fg2a': 3, 'fg3m': 0, 'fg3a': 1}
    """
    # Initialize counters for all shot types
    results = {"ftm": 0, "fta": 0, "fg2m": 0, "fg2a": 0, "fg3m": 0, "fg3a": 0}

    # Return default values if shot_string is empty
    if not shot_string or shot_string.strip() == "":
        return results

    # Count shots by type
    for char in shot_string:
        if char not in shot_mapping:
            continue  # Skip any characters not in the mapping

        shot_info = shot_mapping[char]
        shot_type = shot_info.get("type")

        # Update the appropriate counters based on shot type and outcome
        if shot_type == "FT":
            results["fta"] += 1
            if shot_info.get("made"):
                results["ftm"] += 1
        elif shot_type == "2P":
            results["fg2a"] += 1
            if shot_info.get("made"):
                results["fg2m"] += 1
        elif shot_type == "3P":
            results["fg3a"] += 1
            if shot_info.get("made"):
                results["fg3m"] += 1

    return results
