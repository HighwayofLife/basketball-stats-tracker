"""Unit tests for player portrait template helper functions."""

from unittest.mock import Mock, patch

from app.data_access.models import Player
from app.web_ui.templates_config import (
    clear_player_portrait_cache,
    player_portrait_url,
)


class TestPlayerPortraitTemplateHelpers:
    """Test cases for player portrait template helper functions."""

    def test_player_portrait_url_with_player_object(self):
        """Test player_portrait_url with a Player object."""
        # Create a mock player object
        player = Mock(spec=Player)
        player.id = 123
        player.thumbnail_image = "players/123/portrait.jpg"

        # Mock the cached database lookup (now using consolidated function)
        with patch("app.web_ui.templates_config._get_cached_entity_image_data") as mock_get_data:
            mock_get_data.return_value = "players/123/portrait.jpg"

            # Mock file existence check
            with patch("app.web_ui.templates_config._check_file_exists") as mock_exists:
                mock_exists.return_value = True

                url = player_portrait_url(player)

                assert url == "/uploads/players/123/portrait.jpg"
                mock_get_data.assert_called_once_with(123, "player")

    def test_player_portrait_url_with_dict(self):
        """Test player_portrait_url with a dictionary."""
        player_dict = {"id": 456, "name": "Test Player", "thumbnail_image": "players/456/portrait.png"}

        # Mock the cached database lookup
        with patch("app.web_ui.templates_config._get_cached_entity_image_data") as mock_get_data:
            mock_get_data.return_value = "players/456/portrait.png"

            # Mock file existence check
            with patch("app.web_ui.templates_config._check_file_exists") as mock_exists:
                mock_exists.return_value = True

                url = player_portrait_url(player_dict)

                assert url == "/uploads/players/456/portrait.png"
                mock_get_data.assert_called_once_with(456, "player")

    def test_player_portrait_url_no_portrait(self):
        """Test player_portrait_url when player has no portrait."""
        player = Mock(spec=Player)
        player.id = 789
        player.thumbnail_image = None

        # Mock the cached database lookup to return None
        with patch("app.web_ui.templates_config._get_cached_entity_image_data") as mock_get_data:
            mock_get_data.return_value = None

            url = player_portrait_url(player)

            assert url is None
            mock_get_data.assert_called_once_with(789, "player")

    def test_player_portrait_url_file_not_exists(self):
        """Test player_portrait_url when portrait file doesn't exist."""
        player = Mock(spec=Player)
        player.id = 123
        player.thumbnail_image = "players/123/portrait.jpg"

        # Mock the cached database lookup
        with patch("app.web_ui.templates_config._get_cached_entity_image_data") as mock_get_data:
            mock_get_data.return_value = "players/123/portrait.jpg"

            # Mock file existence check to return False
            with patch("app.web_ui.templates_config._check_file_exists") as mock_exists:
                mock_exists.return_value = False

                url = player_portrait_url(player)

                assert url is None

    def test_player_portrait_url_none_player(self):
        """Test player_portrait_url with None player."""
        url = player_portrait_url(None)
        assert url is None

    def test_player_portrait_url_invalid_player(self):
        """Test player_portrait_url with invalid player object."""
        # Object without id attribute
        invalid_player = Mock()
        invalid_player.name = "Test"
        # Ensure this mock doesn't have an id attribute
        if hasattr(invalid_player, "id"):
            delattr(invalid_player, "id")

        url = player_portrait_url(invalid_player)
        assert url is None

    def test_player_portrait_url_with_uploads_prefix(self):
        """Test player_portrait_url when filename already has uploads prefix."""
        player = Mock(spec=Player)
        player.id = 123
        player.thumbnail_image = "uploads/players/123/portrait.jpg"

        # Mock the cached database lookup
        with patch("app.web_ui.templates_config._get_cached_entity_image_data") as mock_get_data:
            mock_get_data.return_value = "uploads/players/123/portrait.jpg"

            # Mock file existence check
            with patch("app.web_ui.templates_config._check_file_exists") as mock_exists:
                mock_exists.return_value = True

                url = player_portrait_url(player)

                # Should strip the duplicate "uploads/" prefix
                assert url == "/uploads/players/123/portrait.jpg"

    def test_player_portrait_url_database_error_returns_none(self):
        """Test player_portrait_url returns None when database lookup fails."""
        player = Mock(spec=Player)
        player.id = 123
        player.thumbnail_image = "players/123/portrait.jpg"

        # Mock the cached database lookup to fail
        with patch("app.web_ui.templates_config._get_cached_entity_image_data") as mock_get_data:
            # Make the cached lookup return None (no image data found)
            mock_get_data.return_value = None

            url = player_portrait_url(player)

            assert url is None
            mock_get_data.assert_called_once_with(123, "player")

    def test_player_portrait_url_file_not_exists_returns_none(self):
        """Test player_portrait_url returns None when file doesn't exist."""
        player = Mock(spec=Player)
        player.id = 123
        player.thumbnail_image = "players/123/portrait.jpg"

        # Mock the cached database lookup to return a filename
        with patch("app.web_ui.templates_config._get_cached_entity_image_data") as mock_get_data:
            mock_get_data.return_value = "players/123/portrait.jpg"

            # Mock file existence check to return False
            with patch("app.web_ui.templates_config._check_file_exists") as mock_check:
                mock_check.return_value = False

                url = player_portrait_url(player)

                assert url is None
                mock_check.assert_called_once()

    def test_clear_player_portrait_cache(self):
        """Test clearing player portrait cache."""
        # Mock the cache clear function for the new consolidated structure
        with patch("app.web_ui.templates_config._get_cached_entity_image_data.cache_clear") as mock_clear:
            with patch("app.web_ui.templates_config._check_file_exists.cache_clear") as mock_clear_exists:
                # Clear cache for all players
                clear_player_portrait_cache()

                mock_clear.assert_called_once()
                mock_clear_exists.assert_called_once()

    def test_clear_player_portrait_cache_specific_player(self):
        """Test clearing player portrait cache for specific player."""
        # Mock the cache clear function
        with patch("app.web_ui.templates_config._get_cached_entity_image_data.cache_clear") as mock_clear:
            with patch("app.web_ui.templates_config._check_file_exists.cache_clear") as mock_clear_exists:
                # Clear cache for specific player (note: current implementation clears all)
                clear_player_portrait_cache(player_id=123)

                # Currently clears all cache entries
                mock_clear.assert_called_once()

    def test_cached_entity_image_data_player(self):
        """Test the cached entity image data function for players."""
        # Note: This is testing the internal function for completeness
        from app.web_ui.templates_config import _get_cached_entity_image_data

        player_id = 123

        with patch("app.data_access.db_session.get_db_session") as mock_get_session:
            mock_session = Mock()
            mock_get_session.return_value.__enter__.return_value = mock_session

            # Mock the player query
            mock_player = Mock(spec=Player)
            mock_player.thumbnail_image = "players/123/portrait.jpg"

            mock_query = Mock()
            mock_query.filter.return_value.first.return_value = mock_player
            mock_session.query.return_value = mock_query

            # Clear cache before test
            _get_cached_entity_image_data.cache_clear()

            # Call the function with player entity type
            result = _get_cached_entity_image_data(player_id, "player")

            assert result == "players/123/portrait.jpg"

    def test_cached_entity_image_data_no_player(self):
        """Test cached entity image data when player doesn't exist."""
        from app.web_ui.templates_config import _get_cached_entity_image_data

        player_id = 999

        with patch("app.data_access.db_session.get_db_session") as mock_get_session:
            mock_session = Mock()
            mock_get_session.return_value.__enter__.return_value = mock_session

            # Mock the player query to return None
            mock_query = Mock()
            mock_query.filter.return_value.first.return_value = None
            mock_session.query.return_value = mock_query

            # Clear cache before test
            _get_cached_entity_image_data.cache_clear()

            # Call the function
            result = _get_cached_entity_image_data(player_id, "player")

            assert result is None
