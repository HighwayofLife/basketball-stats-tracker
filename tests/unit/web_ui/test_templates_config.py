"""Unit tests for templates_config helpers."""

from unittest.mock import Mock, patch

import pytest

from app.web_ui.templates_config import team_logo_url


class TestTemplatesConfig:
    """Test cases for template configuration helpers."""

    def test_team_logo_url_success(self):
        """Test successful team logo URL generation."""
        # Create mock team
        mock_team = Mock()
        mock_team.id = 123

        with patch("app.web_ui.templates_config.ImageProcessingService.get_team_logo_url") as mock_get_url:
            mock_get_url.return_value = "/static/uploads/teams/123/120x120/logo.jpg"

            result = team_logo_url(mock_team, "120x120")

            assert result == "/static/uploads/teams/123/120x120/logo.jpg"
            mock_get_url.assert_called_once_with(123, "120x120")

    def test_team_logo_url_default_size(self):
        """Test team logo URL generation with default size."""
        # Create mock team
        mock_team = Mock()
        mock_team.id = 456

        with patch("app.web_ui.templates_config.ImageProcessingService.get_team_logo_url") as mock_get_url:
            mock_get_url.return_value = "/static/uploads/teams/456/120x120/logo.png"

            result = team_logo_url(mock_team)  # No size specified, should use default

            assert result == "/static/uploads/teams/456/120x120/logo.png"
            mock_get_url.assert_called_once_with(456, "120x120")  # Default size

    def test_team_logo_url_no_logo_exists(self):
        """Test team logo URL generation when no logo exists."""
        # Create mock team
        mock_team = Mock()
        mock_team.id = 789

        with patch("app.web_ui.templates_config.ImageProcessingService.get_team_logo_url") as mock_get_url:
            mock_get_url.return_value = None  # No logo exists

            result = team_logo_url(mock_team, "64x64")

            assert result is None
            mock_get_url.assert_called_once_with(789, "64x64")

    def test_team_logo_url_none_team(self):
        """Test team logo URL generation with None team."""
        result = team_logo_url(None, "120x120")
        assert result is None

    def test_team_logo_url_team_without_id(self):
        """Test team logo URL generation with team that has no id attribute."""
        mock_team = Mock()
        # Don't set id attribute, or delete it
        if hasattr(mock_team, "id"):
            delattr(mock_team, "id")

        result = team_logo_url(mock_team, "120x120")
        assert result is None

    def test_team_logo_url_different_sizes(self):
        """Test team logo URL generation with different sizes."""
        mock_team = Mock()
        mock_team.id = 100

        test_cases = [
            ("original", "/static/uploads/teams/100/original/logo.jpg"),
            ("120x120", "/static/uploads/teams/100/120x120/logo.jpg"),
            ("64x64", "/static/uploads/teams/100/64x64/logo.jpg"),
        ]

        for size, expected_url in test_cases:
            with patch("app.web_ui.templates_config.ImageProcessingService.get_team_logo_url") as mock_get_url:
                mock_get_url.return_value = expected_url

                result = team_logo_url(mock_team, size)

                assert result == expected_url
                mock_get_url.assert_called_once_with(100, size)

    def test_team_logo_url_with_string_id(self):
        """Test team logo URL generation when team id is a string."""
        mock_team = Mock()
        mock_team.id = "123"  # String ID (should still work)

        with patch("app.web_ui.templates_config.ImageProcessingService.get_team_logo_url") as mock_get_url:
            mock_get_url.return_value = "/static/uploads/teams/123/120x120/logo.jpg"

            result = team_logo_url(mock_team, "120x120")

            assert result == "/static/uploads/teams/123/120x120/logo.jpg"
            mock_get_url.assert_called_once_with("123", "120x120")

    def test_team_logo_url_error_handling(self):
        """Test team logo URL generation when service raises exception."""
        mock_team = Mock()
        mock_team.id = 123

        with patch("app.web_ui.templates_config.ImageProcessingService.get_team_logo_url") as mock_get_url:
            mock_get_url.side_effect = RuntimeError("File system error")

            # Should propagate the exception from the service
            with pytest.raises(RuntimeError, match="File system error"):
                team_logo_url(mock_team, "120x120")
