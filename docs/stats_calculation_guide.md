# Basketball Statistics Calculation Guide

This document outlines the formulas and methodologies used for calculating various basketball statistics within the Python Basketball Stats Tracker application.

## 1. Shooting Percentage

**Formula:** `Percentage = Makes / Attempts`

**Description:** Calculates the ratio of successful shots (makes) to total shots attempted.

**Args:**
*   `makes` (int): Number of successful shots.
*   `attempts` (int): Number of total shot attempts.

**Returns:**
*   `float | None`: The percentage as a float between 0.0 and 1.0. Returns `None` if `attempts` is 0 to avoid division by zero errors.

**Example:**
*   `calculate_percentage(makes=7, attempts=10)` returns `0.7`.
*   `calculate_percentage(makes=0, attempts=0)` returns `None`.

## 2. Total Points

**Formula:** `Points = (Free Throws Made * 1) + (2-Point Field Goals Made * 2) + (3-Point Field Goals Made * 3)`

**Description:** Calculates the total points scored by a player or team.

**Args:**
*   `ftm` (int): Number of free throws made.
*   `fg2m` (int): Number of 2-point field goals made.
*   `fg3m` (int): Number of 3-point field goals made.

**Returns:**
*   `int`: Total points scored.

**Example:**
*   `calculate_points(ftm=5, fg2m=10, fg3m=3)` returns `34` (i.e., `(5*1) + (10*2) + (3*3)`).

## 3. Effective Field Goal Percentage (eFG%)

**Formula:** `eFG% = (Field Goals Made + 0.5 * 3-Point Field Goals Made) / Total Field Goal Attempts`

**Description:** Adjusts field goal percentage to account for the fact that 3-point field goals are worth more than 2-point field goals.

**Args:**
*   `total_fgm` (int): Total field goals made (both 2-point and 3-point).
*   `fg3m` (int): Number of 3-point field goals made.
*   `total_fga` (int): Total field goal attempts (both 2-point and 3-point).

**Returns:**
*   `float | None`: The eFG% as a float. Returns `None` if `total_fga` is 0.

**Example:**
*   `calculate_efg(total_fgm=13, fg3m=3, total_fga=20)` returns `0.725` (i.e., `(13 + 0.5 * 3) / 20`).
*   `calculate_efg(total_fgm=0, fg3m=0, total_fga=0)` returns `None`.

## 4. True Shooting Percentage (TS%)

**Formula:** `TS% = Total Points / (2 * (Total Field Goal Attempts + 0.44 * Free Throw Attempts))`

**Description:** Measures a player's shooting efficiency by taking into account free throws, 2-point field goals, and 3-point field goals. The factor `0.44` approximates the number of possessions used per free throw attempt (typically a pair of free throws results from one foul, and not all shooting fouls result in free throws).

**Args:**
*   `points` (int): Total points scored.
*   `total_fga` (int): Total field goal attempts.
*   `fta` (int): Free throw attempts.

**Returns:**
*   `float | None`: The TS% as a float. Returns `None` if the denominator `(2 * (total_fga + 0.44 * fta))` is 0.

**Example:**
*   `calculate_ts(points=25, total_fga=15, fta=10)`:
    *   Denominator = `2 * (15 + 0.44 * 10)`
    *   Denominator = `2 * (15 + 4.4)`
    *   Denominator = `2 * 19.4`
    *   Denominator = `38.8`
    *   TS% = `25 / 38.8`
    *   TS% ≈ `0.644329...`
    *   Returns approximately `0.644` (when rounded to three decimal places).
*   `calculate_ts(points=50, total_fga=40, fta=10)`:
    *   Denominator = `2 * (40 + 0.44 * 10)`
    *   Denominator = `2 * (40 + 4.4)`
    *   Denominator = `2 * 44.4`
    *   Denominator = `88.8`
    *   TS% = `50 / 88.8`
    *   TS% ≈ `0.563063...`
    *   Returns approximately `0.563` (when rounded to three decimal places).
*   `calculate_ts(points=0, total_fga=0, fta=0)` returns `None`.

## 5. Points Per Shot Attempt (PPSA)

**Formula:** `PPSA = Total Points / (Total Field Goal Attempts + Free Throw Attempts)`

**Description:** Measures offensive efficiency in terms of points generated per shot attempt. Unlike Points Per Possession (PPP), this metric doesn't require tracking possessions, making it more practical for basic box score stats.

**Args:**
*   `points` (int): Total points scored.
*   `total_fga` (int): Total field goal attempts.
*   `fta` (int): Free throw attempts.

**Returns:**
*   `float | None`: The PPSA as a float. Returns `None` if there are no shot attempts.

**Example:**
*   `calculate_ppsa(points=30, total_fga=20, fta=10)`:
    *   Total attempts = `20 + 10 = 30`
    *   PPSA = `30 / 30 = 1.0`
    *   Returns `1.0` points per shot attempt.
*   `calculate_ppsa(points=40, total_fga=20, fta=5)`:
    *   Total attempts = `20 + 5 = 25`
    *   PPSA = `40 / 25 = 1.6`
    *   Returns `1.6` points per shot attempt, indicating high efficiency.
*   `calculate_ppsa(points=0, total_fga=0, fta=0)` returns `None`.

## 6. Scoring Distribution

**Formula:** For each shot type, `Percentage = Points from Shot Type / Total Points`

**Description:** Calculates the distribution of points by shot type (free throws, 2-point field goals, and 3-point field goals). This provides insight into a player's or team's scoring balance and dependence on different shot types.

**Args:**
*   `ft_points` (int): Points from free throws (FTM * 1).
*   `fg2_points` (int): Points from 2-point field goals (2PM * 2).
*   `fg3_points` (int): Points from 3-point field goals (3PM * 3).

**Returns:**
*   `dict[str, float | None]`: A dictionary with keys 'ft_pct', 'fg2_pct', 'fg3_pct' containing the percentage (0.0 to 1.0) of points from each shot type. Returns None for all values if total points is 0.

**Example:**
*   `calculate_scoring_distribution(ft_points=15, fg2_points=30, fg3_points=15)`:
    *   Total points = `15 + 30 + 15 = 60`
    *   FT percentage = `15 / 60 = 0.25` (25% of points from free throws)
    *   2P percentage = `30 / 60 = 0.5` (50% of points from 2-pointers)
    *   3P percentage = `15 / 60 = 0.25` (25% of points from 3-pointers)
    *   Returns `{'ft_pct': 0.25, 'fg2_pct': 0.5, 'fg3_pct': 0.25}`
*   `calculate_scoring_distribution(ft_points=0, fg2_points=0, fg3_points=0)` returns `{'ft_pct': None, 'fg2_pct': None, 'fg3_pct': None}`.
