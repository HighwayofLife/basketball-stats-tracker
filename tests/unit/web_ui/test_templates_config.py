"""Unit tests for templates_config helpers."""

from unittest.mock import Mock, patch

from app.config import UPLOADS_URL_PREFIX
from app.web_ui.templates_config import clear_team_logo_cache, team_logo_url


class TestTeamLogoUrl:
    """Test cases for team_logo_url function."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_team_logo_cache()

    def teardown_method(self):
        """Clear cache after each test."""
        clear_team_logo_cache()

    def test_team_logo_url_with_valid_team_object(self):
        """Test team logo URL generation with valid team object that has logo."""
        mock_team = Mock()
        mock_team.id = 123

        # Mock the database query
        mock_team_obj = Mock()
        mock_team_obj.logo_filename = "teams/123/logo.png"

        with (
            patch("app.data_access.db_session.get_db_session") as mock_get_db,
            patch("app.data_access.models") as mock_models,
            patch("app.config.settings") as mock_settings,
            patch("pathlib.Path.exists") as mock_exists,
        ):
            # Setup database mock
            mock_session = Mock()
            mock_get_db.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = mock_team_obj

            # Setup settings mock
            mock_settings.UPLOAD_DIR = "/uploads"

            # Mock file exists
            mock_exists.return_value = True

            result = team_logo_url(mock_team)

            assert result == f"{UPLOADS_URL_PREFIX}teams/123/logo.png"

    def test_team_logo_url_with_dict_input(self):
        """Test team logo URL generation with dict input."""
        team_dict = {"id": 456}

        # Mock the database query
        mock_team_obj = Mock()
        mock_team_obj.logo_filename = "teams/456/logo.jpg"

        with (
            patch("app.data_access.db_session.get_db_session") as mock_get_db,
            patch("app.data_access.models") as mock_models,
            patch("app.config.settings") as mock_settings,
            patch("pathlib.Path.exists") as mock_exists,
        ):
            # Setup database mock
            mock_session = Mock()
            mock_get_db.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = mock_team_obj

            # Setup settings mock
            mock_settings.UPLOAD_DIR = "/uploads"

            # Mock file exists
            mock_exists.return_value = True

            result = team_logo_url(team_dict)

            assert result == f"{UPLOADS_URL_PREFIX}teams/456/logo.jpg"

    def test_team_logo_url_no_logo_filename_in_db(self):
        """Test team logo URL when team has no logo_filename in database."""
        mock_team = Mock()
        mock_team.id = 789
        # Ensure the mock doesn't have logo_filename
        if hasattr(mock_team, "logo_filename"):
            delattr(mock_team, "logo_filename")

        # Mock the cached database lookup to return None
        with patch("app.web_ui.templates_config._get_cached_entity_image_data") as mock_get_data:
            mock_get_data.return_value = None

            result = team_logo_url(mock_team)

            assert result is None
            mock_get_data.assert_called_once_with(789, "team")

    def test_team_logo_url_team_not_found_in_db(self):
        """Test team logo URL when team is not found in database."""
        mock_team = Mock()
        mock_team.id = 999
        # Ensure the mock doesn't have logo_filename
        if hasattr(mock_team, "logo_filename"):
            delattr(mock_team, "logo_filename")

        # Mock the cached database lookup to return None (team not found)
        with patch("app.web_ui.templates_config._get_cached_entity_image_data") as mock_get_data:
            mock_get_data.return_value = None

            result = team_logo_url(mock_team)

            assert result is None
            mock_get_data.assert_called_once_with(999, "team")

    def test_team_logo_url_file_does_not_exist(self):
        """Test team logo URL when database has filename but file doesn't exist."""
        mock_team = Mock()
        mock_team.id = 123

        # Mock the database query - team has logo_filename but file doesn't exist
        mock_team_obj = Mock()
        mock_team_obj.logo_filename = "teams/123/logo.png"

        with (
            patch("app.web_ui.templates_config._get_cached_entity_image_data") as mock_cached_data,
            patch("app.config.settings") as mock_settings,
            patch("pathlib.Path.exists") as mock_exists,
        ):
            # Setup cached database mock
            mock_cached_data.return_value = "teams/123/logo.png"

            # Setup settings mock
            mock_settings.UPLOAD_DIR = "/uploads"

            # Mock file doesn't exist
            mock_exists.return_value = False

            result = team_logo_url(mock_team)

            assert result is None

    def test_team_logo_url_handles_uploads_prefix_in_filename(self):
        """Test team logo URL handles logo_filename with uploads/ prefix."""
        mock_team = Mock()
        mock_team.id = 123

        # Mock the database query - team has logo_filename with uploads/ prefix
        mock_team_obj = Mock()
        mock_team_obj.logo_filename = "uploads/teams/123/logo.png"

        with (
            patch("app.data_access.db_session.get_db_session") as mock_get_db,
            patch("app.data_access.models") as mock_models,
            patch("app.config.settings") as mock_settings,
            patch("pathlib.Path.exists") as mock_exists,
        ):
            # Setup database mock
            mock_session = Mock()
            mock_get_db.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = mock_team_obj

            # Setup settings mock
            mock_settings.UPLOAD_DIR = "/uploads"

            # Mock file exists
            mock_exists.return_value = True

            result = team_logo_url(mock_team)

            assert result == f"{UPLOADS_URL_PREFIX}teams/123/logo.png"

    def test_team_logo_url_none_input(self):
        """Test team logo URL with None input."""
        result = team_logo_url(None)
        assert result is None

    def test_team_logo_url_no_id_attribute(self):
        """Test team logo URL with object that has no id."""
        mock_team = Mock()
        if hasattr(mock_team, "id"):
            delattr(mock_team, "id")

        result = team_logo_url(mock_team)
        assert result is None

    def test_team_logo_url_empty_dict(self):
        """Test team logo URL with empty dict."""
        result = team_logo_url({})
        assert result is None

    def test_team_logo_url_database_error_returns_none(self):
        """Test team logo URL returns None on database error."""
        mock_team = Mock()
        mock_team.id = 123

        with patch("app.web_ui.templates_config._get_cached_entity_image_data") as mock_cached_data:
            # Mock database error - returns None when no data found
            mock_cached_data.return_value = None

            result = team_logo_url(mock_team)

            assert result is None
            mock_cached_data.assert_called_once_with(123, "team")
