"""
Test module for stats_calculator.py
"""


from app.utils.stats_calculator import calculate_efg, calculate_percentage, calculate_points, calculate_ts


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
        assert round(result, 3) == 0.667

    def test_ts_with_mixed_shots(self):
        """Tests calculating TS with mixed shot types."""
        # 25 points, 15 FGA, 10 FTA
        # TS = 25 / (2 * (15 + 0.44*10)) = 25/34.4 = 0.727
        result = calculate_ts(25, 15, 10)
        assert round(result, 3) == 0.727
