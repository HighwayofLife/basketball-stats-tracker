"""
Utility for calculating derived basketball statistics from raw data.
"""


def calculate_percentage(makes: int, attempts: int) -> float | None:
    """
    Calculate a shooting percentage (makes divided by attempts).

    Args:
        makes: Number of successful shots
        attempts: Number of total shot attempts

    Returns:
        The percentage as a float between 0.0 and 1.0, or None if attempts is 0

    Example:
        >>> calculate_percentage(7, 10)
        0.7
    """
    if attempts == 0:
        return None
    return makes / attempts


def calculate_points(ftm: int, fg2m: int, fg3m: int) -> int:
    """
    Calculate total points scored.

    Args:
        ftm: Number of free throws made (1 point each)
        fg2m: Number of 2-point field goals made (2 points each)
        fg3m: Number of 3-point field goals made (3 points each)

    Returns:
        Total points

    Example:
        >>> calculate_points(5, 10, 3)
        34  # (5*1) + (10*2) + (3*3)
    """
    return ftm + (fg2m * 2) + (fg3m * 3)


def calculate_efg(total_fgm: int, fg3m: int, total_fga: int) -> float | None:
    """
    Calculate Effective Field Goal Percentage (eFG%).

    eFG% = (FGM + 0.5 * 3PM) / FGA

    Args:
        total_fgm: Total field goals made (both 2-point and 3-point)
        fg3m: Number of 3-point field goals made
        total_fga: Total field goal attempts

    Returns:
        The eFG% as a float between 0.0 and 1.0, or None if total_fga is 0

    Example:
        >>> calculate_efg(13, 3, 20)
        0.725  # (13 + 0.5*3) / 20
    """
    if total_fga == 0:
        return None
    return (total_fgm + 0.5 * fg3m) / total_fga


def calculate_ts(points: int, total_fga: int, fta: int) -> float | None:
    """
    Calculate True Shooting Percentage (TS%).

    TS% = Points / (2 * (FGA + 0.44 * FTA))

    Args:
        points: Total points scored
        total_fga: Total field goal attempts
        fta: Free throw attempts

    Returns:
        The TS% as a float between 0.0 and 1.0, or None if denominator is 0

    Example:
        >>> calculate_ts(50, 40, 10)
        0.595  # 50 / (2 * (40 + 0.44*10))
    """
    denominator = 2 * (total_fga + 0.44 * fta)
    if denominator == 0:
        return None
    return points / denominator
