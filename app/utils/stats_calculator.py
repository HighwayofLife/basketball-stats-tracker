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
        >>> calculate_ts(25, 15, 10)  # Expected: 25 / (2 * (15 + 0.44*10)) = 25 / 38.8 ~ 0.644
        0.6443298969072165
        >>> calculate_ts(50, 40, 10) # Expected: 50 / (2 * (40 + 0.44*10)) = 50 / 88.8 ~ 0.563
        0.5630630630630631
    """
    denominator = 2 * (total_fga + 0.44 * fta)
    if denominator == 0:
        return None
    return points / denominator


def calculate_ppsa(points: int, total_fga: int, fta: int) -> float | None:
    """
    Calculate Points Per Shot Attempt (PPSA).

    PPSA = Points / (FGA + FTA)

    This metric measures the offensive efficiency in terms of points generated per shot attempt,
    including both field goals and free throws.

    Args:
        points: Total points scored
        total_fga: Total field goal attempts
        fta: Free throw attempts

    Returns:
        The PPSA as a float, or None if there are no shot attempts

    Example:
        >>> calculate_ppsa(30, 20, 10)  # 30 points on 20 FGA and 10 FTA
        1.0  # 30 / (20 + 10) = 1.0 points per shot attempt
    """
    total_attempts = total_fga + fta
    if total_attempts == 0:
        return None
    return points / total_attempts


def calculate_scoring_distribution(ft_points: int, fg2_points: int, fg3_points: int) -> dict[str, float | None]:
    """
    Calculate the distribution of points by shot type.

    Computes the percentage of total points coming from free throws,
    2-point field goals, and 3-point field goals.

    Args:
        ft_points: Points from free throws (FTM * 1)
        fg2_points: Points from 2-point field goals (2PM * 2)
        fg3_points: Points from 3-point field goals (3PM * 3)

    Returns:
        A dictionary with keys 'ft_pct', 'fg2_pct', 'fg3_pct' containing
        the percentage (0.0 to 1.0) of points from each shot type.
        Returns None for all values if total points is 0.

    Example:
        >>> calculate_scoring_distribution(10, 20, 15)  # 10 pts FT, 20 pts 2P, 15 pts 3P
        {'ft_pct': 0.222, 'fg2_pct': 0.444, 'fg3_pct': 0.333}  # percentages of 45 total points
    """
    total_points = ft_points + fg2_points + fg3_points

    if total_points == 0:
        return {"ft_pct": None, "fg2_pct": None, "fg3_pct": None}

    return {
        "ft_pct": ft_points / total_points,
        "fg2_pct": fg2_points / total_points,
        "fg3_pct": fg3_points / total_points,
    }
