"""
Test module for stats_calculator.py
"""

from app.utils.stats_calculator import (
    calculate_efg,
    calculate_percentage,
    calculate_points,
    calculate_ppsa,
    calculate_scoring_distribution,
    calculate_ts,
)


class TestCalculatePercentage:
    """Tests for the calculate_percentage function."""

    def test_positive_percentage(self):
        """Tests calculating a valid percentage."""
        result = calculate_percentage(7, 10)
        assert result == 0.7

    def test_zero_attempts(self):
        """Tests calculating a percentage with zero attempts."""
        result = calculate_percentage(0, 0)
        assert result is None

    def test_perfect_percentage(self):
        """Tests calculating a 100% percentage."""
        result = calculate_percentage(10, 10)
        assert result == 1.0

    def test_zero_makes(self):
        """Tests calculating a percentage with zero makes."""
        result = calculate_percentage(0, 10)
        assert result == 0.0


class TestCalculatePoints:
    """Tests for the calculate_points function."""

    def test_no_points(self):
        """Tests calculating points with all zeros."""
        result = calculate_points(0, 0, 0)
        assert result == 0

    def test_all_shot_types(self):
        """Tests calculating points with various shot types."""
        # 3 free throws (1 point each) +
        # 2 two-pointers (2 points each) +
        # 1 three-pointer (3 points)
        # = 3 + 4 + 3 = 10 points
        result = calculate_points(3, 2, 1)
        assert result == 10

    def test_only_free_throws(self):
        """Tests calculating points with only free throws."""
        result = calculate_points(5, 0, 0)
        assert result == 5

    def test_only_two_pointers(self):
        """Tests calculating points with only 2-pointers."""
        result = calculate_points(0, 5, 0)
        assert result == 10

    def test_only_three_pointers(self):
        """Tests calculating points with only 3-pointers."""
        result = calculate_points(0, 0, 5)
        assert result == 15


class TestCalculateEfg:
    """Tests for the calculate_efg function."""

    def test_efg_with_no_attempts(self):
        """Tests calculating EFG with no attempts."""
        result = calculate_efg(0, 0, 0)
        assert result is None

    def test_efg_with_only_twos(self):
        """Tests calculating EFG with only two-pointers."""
        # 5 made out of 10 attempts, all 2-pointers
        # EFG = (5 + 0.5*0) / 10 = 0.5
        result = calculate_efg(5, 0, 10)
        assert result == 0.5

    def test_efg_with_mixed_shots(self):
        """Tests calculating EFG with mixed shot types."""
        # 3 made FG, 2 of which are 3-pointers, 10 total attempts
        # EFG = (3 + 0.5*2) / 10 = 0.4
        result = calculate_efg(3, 2, 10)
        assert result == 0.4

    def test_efg_with_only_threes(self):
        """Tests calculating EFG with only three-pointers."""
        # 4 made 3-pointers out of 8 attempts
        # EFG = (4 + 0.5*4) / 8 = 6/8 = 0.75
        result = calculate_efg(4, 4, 8)
        assert result == 0.75

    def test_perfect_efg(self):
        """Tests calculating EFG with perfect shooting."""
        # All shots made, including some 3-pointers
        # EFG = (10 + 0.5*5) / 10 = 12.5/10 = 1.25
        result = calculate_efg(10, 5, 10)
        assert result == 1.25


class TestCalculateTs:
    """Tests for the calculate_ts function."""

    def test_ts_with_no_attempts(self):
        """Tests calculating TS with no attempts."""
        result = calculate_ts(0, 0, 0)
        assert result is None

    def test_ts_with_only_field_goals(self):
        """Tests calculating TS with only field goals."""
        # 20 points, 15 FGA, 0 FTA
        # TS = 20 / (2 * (15 + 0.44*0)) = 20/30 = 0.667
        result = calculate_ts(20, 15, 0)
        assert result is not None
        assert round(result, 3) == 0.667

    def test_ts_with_mixed_shots(self):
        """Tests calculating TS with mixed shot types."""
        # 25 points, 15 FGA, 10 FTA
        # TS = 25 / (2 * (15 + 0.44*10)) = 25 / (2 * (15 + 4.4)) = 25 / (2 * 19.4) = 25 / 38.8
        # TS approx 0.644329...
        result = calculate_ts(25, 15, 10)
        assert result is not None
        assert round(result, 3) == 0.644

    def test_ts_with_only_free_throws(self):
        """Tests calculating TS with only free throws."""
        # 10 points, 0 FGA, 10 FTA
        # TS = 10 / (2 * (0 + 0.44*10)) = 10 / (2 * 4.4) = 10 / 8.8 = 1.136
        result = calculate_ts(10, 0, 10)
        assert result is not None
        assert round(result, 3) == 1.136

    def test_ts_with_high_efficiency(self):
        """Tests calculating TS with high efficiency scoring."""
        # 30 points, 10 FGA, 5 FTA - very efficient scoring
        # TS = 30 / (2 * (10 + 0.44*5)) = 30 / (2 * (10 + 2.2)) = 30 / (2 * 12.2) = 30 / 24.4 = 1.23
        result = calculate_ts(30, 10, 5)
        assert result is not None
        assert round(result, 3) == 1.23


class TestCalculatePpsa:
    """Tests for the calculate_ppsa function."""

    def test_ppsa_with_no_attempts(self):
        """Tests calculating PPSA with no shot attempts."""
        result = calculate_ppsa(0, 0, 0)
        assert result is None

    def test_ppsa_typical_value(self):
        """Tests calculating a typical PPSA value."""
        # 30 points on 20 FGA and 10 FTA
        # PPSA = 30/(20+10) = 30/30 = 1.0
        result = calculate_ppsa(30, 20, 10)
        assert result is not None
        assert round(result, 3) == 1.0

    def test_ppsa_high_value(self):
        """Tests calculating a high PPSA value."""
        # 40 points on 20 FGA and 5 FTA
        # PPSA = 40/(20+5) = 40/25 = 1.6
        result = calculate_ppsa(40, 20, 5)
        assert result is not None
        assert round(result, 3) == 1.6

    def test_ppsa_low_value(self):
        """Tests calculating a low PPSA value."""
        # 15 points on 20 FGA and 10 FTA
        # PPSA = 15/(20+10) = 15/30 = 0.5
        result = calculate_ppsa(15, 20, 10)
        assert result is not None
        assert round(result, 3) == 0.5


class TestCalculateScoringDistribution:
    """Tests for the calculate_scoring_distribution function."""

    def test_distribution_with_no_points(self):
        """Tests calculating scoring distribution with no points scored."""
        result = calculate_scoring_distribution(0, 0, 0)
        assert result["ft_pct"] is None
        assert result["fg2_pct"] is None
        assert result["fg3_pct"] is None

    def test_distribution_even_split(self):
        """Tests calculating an even distribution of points."""
        # 10 points from each type, 30 total
        # Each should be 1/3 of the total
        result = calculate_scoring_distribution(10, 10, 10)
        assert result["ft_pct"] == 1 / 3
        assert result["fg2_pct"] == 1 / 3
        assert result["fg3_pct"] == 1 / 3

    def test_distribution_only_free_throws(self):
        """Tests calculating distribution with only free throws."""
        result = calculate_scoring_distribution(15, 0, 0)
        assert result["ft_pct"] == 1.0
        assert result["fg2_pct"] == 0.0
        assert result["fg3_pct"] == 0.0

    def test_distribution_mixed_scoring(self):
        """Tests calculating a typical mixed scoring distribution."""
        # 15 points FT, 30 points 2P, 15 points 3P = 60 total
        # FT: 15/60 = 0.25, 2P: 30/60 = 0.5, 3P: 15/60 = 0.25
        result = calculate_scoring_distribution(15, 30, 15)
        assert result["ft_pct"] == 0.25
        assert result["fg2_pct"] == 0.5
        assert result["fg3_pct"] == 0.25
