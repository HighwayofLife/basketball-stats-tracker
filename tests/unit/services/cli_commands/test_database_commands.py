"""Unit tests for database-related CLI command handlers."""

from unittest.mock import MagicMock, patch

from app.services.cli_commands.database_commands import DatabaseCommands


class TestDatabaseCommands:
    """Test database-related CLI commands."""

    def test_initialize_database_default(self):
        """Test database initialization with default parameters."""
        with patch("app.services.cli_commands.database_commands.DatabaseAdminService") as mock_service:
            mock_instance = MagicMock()
            mock_service.return_value = mock_instance

            DatabaseCommands.initialize_database()

            mock_service.assert_called_once()
            mock_instance.initialize_schema.assert_called_once_with(force=False, make_migration=False)

    def test_initialize_database_with_force(self):
        """Test database initialization with force flag."""
        with patch("app.services.cli_commands.database_commands.DatabaseAdminService") as mock_service:
            mock_instance = MagicMock()
            mock_service.return_value = mock_instance

            DatabaseCommands.initialize_database(force=True, make_migration=False)

            mock_service.assert_called_once()
            mock_instance.initialize_schema.assert_called_once_with(force=True, make_migration=False)

    def test_initialize_database_with_migration(self):
        """Test database initialization with migration flag."""
        with patch("app.services.cli_commands.database_commands.DatabaseAdminService") as mock_service:
            mock_instance = MagicMock()
            mock_service.return_value = mock_instance

            DatabaseCommands.initialize_database(force=False, make_migration=True)

            mock_service.assert_called_once()
            mock_instance.initialize_schema.assert_called_once_with(force=False, make_migration=True)

    def test_check_database_health_success(self, capsys):
        """Test successful database health check."""
        with patch("app.services.cli_commands.database_commands.DatabaseAdminService") as mock_service:
            mock_instance = MagicMock()
            mock_instance.check_connection.return_value = True
            mock_service.return_value = mock_instance

            result = DatabaseCommands.check_database_health()

            assert result is True
            captured = capsys.readouterr()
            assert "Database connection successful!" in captured.out

    def test_check_database_health_failure(self, capsys):
        """Test failed database health check."""
        with patch("app.services.cli_commands.database_commands.DatabaseAdminService") as mock_service:
            mock_instance = MagicMock()
            mock_instance.check_connection.return_value = False
            mock_service.return_value = mock_instance

            result = DatabaseCommands.check_database_health()

            assert result is False
            captured = capsys.readouterr()
            assert "Database connection test failed!" in captured.out

    @patch("seed.seed_all")
    def test_seed_database(self, mock_seed_all, capsys):
        """Test database seeding."""
        DatabaseCommands.seed_database()

        mock_seed_all.assert_called_once()
        captured = capsys.readouterr()
        assert "Seeding database with development data..." in captured.out
        assert "Database seeding completed." in captured.out
