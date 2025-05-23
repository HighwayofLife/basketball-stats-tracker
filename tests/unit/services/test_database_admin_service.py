# tests/unit/services/test_database_admin_service.py

"""Unit tests for database admin service."""

from unittest.mock import Mock, patch

from app.services.database_admin_service import DatabaseAdminService


class TestDatabaseAdminService:
    """Tests for DatabaseAdminService."""

    @patch("app.services.database_admin_service.db_manager.db_manager.get_engine")
    @patch("app.services.database_admin_service.Config")
    def test_init(self, mock_config, mock_get_engine):
        """Test DatabaseAdminService initialization."""
        mock_engine = Mock()
        mock_get_engine.return_value = mock_engine
        mock_alembic_cfg = Mock()
        mock_config.return_value = mock_alembic_cfg

        service = DatabaseAdminService("sqlite:///test.db", "alembic.ini")

        assert service.db_url == "sqlite:///test.db"
        assert service.alembic_ini_path == "alembic.ini"
        assert service.engine == mock_engine
        assert service.alembic_cfg == mock_alembic_cfg
        mock_get_engine.assert_called_once()
        mock_config.assert_called_once_with("alembic.ini")

    @patch("app.services.database_admin_service.db_manager.db_manager.get_engine")
    @patch("app.services.database_admin_service.Config")
    def test_init_default_alembic_path(self, mock_config, mock_get_engine):
        """Test DatabaseAdminService initialization with default alembic path."""
        mock_engine = Mock()
        mock_get_engine.return_value = mock_engine
        mock_alembic_cfg = Mock()
        mock_config.return_value = mock_alembic_cfg

        service = DatabaseAdminService("sqlite:///test.db")

        assert service.alembic_ini_path == "alembic.ini"
        mock_config.assert_called_once_with("alembic.ini")

    @patch("app.services.database_admin_service.os.makedirs")
    @patch("app.services.database_admin_service.os.path.dirname")
    @patch("app.services.database_admin_service.os.path.abspath")
    @patch("app.services.database_admin_service.db_manager.db_manager.get_engine")
    @patch("app.services.database_admin_service.Config")
    def test_ensure_data_dir_sqlite(self, mock_config, mock_get_engine, mock_abspath, mock_dirname, mock_makedirs):
        """Test ensure_data_dir for SQLite database."""
        mock_get_engine.return_value = Mock()
        mock_config.return_value = Mock()
        mock_abspath.return_value = "/absolute/path/to/test.db"
        mock_dirname.return_value = "/absolute/path/to"

        service = DatabaseAdminService("sqlite:///test.db")
        result = service.ensure_data_dir()

        assert result == "/absolute/path/to"
        mock_abspath.assert_called_once_with("test.db")
        mock_dirname.assert_called_once_with("/absolute/path/to/test.db")
        mock_makedirs.assert_called_once_with("/absolute/path/to", exist_ok=True)

    @patch("app.services.database_admin_service.db_manager.db_manager.get_engine")
    @patch("app.services.database_admin_service.Config")
    def test_ensure_data_dir_non_sqlite(self, mock_config, mock_get_engine):
        """Test ensure_data_dir for non-SQLite database."""
        mock_get_engine.return_value = Mock()
        mock_config.return_value = Mock()

        service = DatabaseAdminService("postgresql://user:pass@localhost/db")
        result = service.ensure_data_dir()

        assert result is None

    @patch("app.services.database_admin_service.Base")
    @patch("app.services.database_admin_service.db_manager.db_manager.get_engine")
    @patch("app.services.database_admin_service.Config")
    def test_drop_all_tables(self, mock_config, mock_get_engine, mock_base):
        """Test drop_all_tables method."""
        mock_engine = Mock()
        mock_get_engine.return_value = mock_engine
        mock_config.return_value = Mock()
        mock_metadata = Mock()
        mock_base.metadata = mock_metadata

        service = DatabaseAdminService("sqlite:///test.db")
        service.drop_all_tables()

        mock_metadata.drop_all.assert_called_once_with(bind=mock_engine)

    @patch("app.services.database_admin_service.command")
    @patch("app.services.database_admin_service.Path")
    @patch("app.services.database_admin_service.db_manager.db_manager.get_engine")
    @patch("app.services.database_admin_service.Config")
    def test_create_migration(self, mock_config, mock_get_engine, mock_path, mock_command):
        """Test create_migration method."""
        mock_get_engine.return_value = Mock()
        mock_alembic_cfg = Mock()
        mock_config.return_value = mock_alembic_cfg
        mock_path_instance = Mock()
        mock_path.return_value = mock_path_instance

        service = DatabaseAdminService("sqlite:///test.db")
        service.create_migration("Test migration")

        mock_path.assert_called_once_with("migrations/versions")
        mock_path_instance.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_command.revision.assert_called_once_with(mock_alembic_cfg, message="Test migration", autogenerate=True)

    @patch("app.services.database_admin_service.command")
    @patch("app.services.database_admin_service.Path")
    @patch("app.services.database_admin_service.db_manager.db_manager.get_engine")
    @patch("app.services.database_admin_service.Config")
    def test_create_migration_default_message(self, mock_config, mock_get_engine, mock_path, mock_command):
        """Test create_migration with default message."""
        mock_get_engine.return_value = Mock()
        mock_alembic_cfg = Mock()
        mock_config.return_value = mock_alembic_cfg
        mock_path_instance = Mock()
        mock_path.return_value = mock_path_instance

        service = DatabaseAdminService("sqlite:///test.db")
        service.create_migration()

        mock_command.revision.assert_called_once_with(
            mock_alembic_cfg, message="Update database schema", autogenerate=True
        )

    @patch("app.services.database_admin_service.command")
    @patch("app.services.database_admin_service.db_manager.db_manager.get_engine")
    @patch("app.services.database_admin_service.Config")
    def test_upgrade_to_head(self, mock_config, mock_get_engine, mock_command):
        """Test upgrade_to_head method."""
        mock_get_engine.return_value = Mock()
        mock_alembic_cfg = Mock()
        mock_config.return_value = mock_alembic_cfg

        service = DatabaseAdminService("sqlite:///test.db")
        service.upgrade_to_head()

        mock_command.upgrade.assert_called_once_with(mock_alembic_cfg, "head")

    @patch("app.services.database_admin_service.db_manager.db_manager.get_engine")
    @patch("app.services.database_admin_service.Config")
    def test_initialize_schema_basic(self, mock_config, mock_get_engine):
        """Test initialize_schema with default parameters."""
        mock_get_engine.return_value = Mock()
        mock_config.return_value = Mock()

        service = DatabaseAdminService("postgresql://user:pass@localhost/db")
        with (
            patch.object(service, "ensure_data_dir") as mock_ensure_dir,
            patch.object(service, "upgrade_to_head") as mock_upgrade,
        ):
            mock_ensure_dir.return_value = None

            service.initialize_schema()

            mock_ensure_dir.assert_called_once()
            mock_upgrade.assert_called_once()

    @patch("app.services.database_admin_service.db_manager.db_manager.get_engine")
    @patch("app.services.database_admin_service.Config")
    def test_initialize_schema_with_force(self, mock_config, mock_get_engine):
        """Test initialize_schema with force=True."""
        mock_get_engine.return_value = Mock()
        mock_config.return_value = Mock()

        service = DatabaseAdminService("sqlite:///test.db")
        with (
            patch.object(service, "ensure_data_dir") as mock_ensure_dir,
            patch.object(service, "drop_all_tables") as mock_drop,
            patch.object(service, "upgrade_to_head") as mock_upgrade,
        ):
            mock_ensure_dir.return_value = "/data/dir"

            service.initialize_schema(force=True)

            mock_ensure_dir.assert_called_once()
            mock_drop.assert_called_once()
            mock_upgrade.assert_called_once()

    @patch("app.services.database_admin_service.db_manager.db_manager.get_engine")
    @patch("app.services.database_admin_service.Config")
    def test_initialize_schema_with_migration(self, mock_config, mock_get_engine):
        """Test initialize_schema with make_migration=True."""
        mock_get_engine.return_value = Mock()
        mock_config.return_value = Mock()

        service = DatabaseAdminService("sqlite:///test.db")
        with (
            patch.object(service, "ensure_data_dir") as mock_ensure_dir,
            patch.object(service, "create_migration") as mock_create_migration,
            patch.object(service, "upgrade_to_head") as mock_upgrade,
        ):
            mock_ensure_dir.return_value = None

            service.initialize_schema(make_migration=True, migration_message="Custom message")

            mock_ensure_dir.assert_called_once()
            mock_create_migration.assert_called_once_with("Custom message")
            mock_upgrade.assert_called_once()

    @patch("app.services.database_admin_service.db_manager.db_manager.get_engine")
    @patch("app.services.database_admin_service.Config")
    def test_initialize_schema_full_options(self, mock_config, mock_get_engine):
        """Test initialize_schema with all options enabled."""
        mock_get_engine.return_value = Mock()
        mock_config.return_value = Mock()

        service = DatabaseAdminService("sqlite:///test.db")
        with (
            patch.object(service, "ensure_data_dir") as mock_ensure_dir,
            patch.object(service, "drop_all_tables") as mock_drop,
            patch.object(service, "create_migration") as mock_create_migration,
            patch.object(service, "upgrade_to_head") as mock_upgrade,
        ):
            mock_ensure_dir.return_value = "/data/dir"

            service.initialize_schema(force=True, make_migration=True, migration_message="Full test")

            mock_ensure_dir.assert_called_once()
            mock_drop.assert_called_once()
            mock_create_migration.assert_called_once_with("Full test")
            mock_upgrade.assert_called_once()

    @patch("app.services.database_admin_service.db_manager.db_manager.get_engine")
    @patch("app.services.database_admin_service.Config")
    def test_initialize_schema_migration_default_messages(self, mock_config, mock_get_engine):
        """Test initialize_schema migration with default messages."""
        mock_get_engine.return_value = Mock()
        mock_config.return_value = Mock()

        service = DatabaseAdminService("sqlite:///test.db")
        with (
            patch.object(service, "ensure_data_dir") as mock_ensure_dir,
            patch.object(service, "create_migration") as mock_create_migration,
            patch.object(service, "upgrade_to_head") as _mock_upgrade,
        ):
            mock_ensure_dir.return_value = None

            # Test with force=True and no custom message
            service.initialize_schema(force=True, make_migration=True)
            mock_create_migration.assert_called_with("Initial database schema")

            # Reset mocks
            mock_create_migration.reset_mock()

            # Test with force=False and no custom message
            service.initialize_schema(force=False, make_migration=True)
            mock_create_migration.assert_called_with("Update database schema")

    @patch("app.services.database_admin_service.db_manager.db_manager.get_engine")
    @patch("app.services.database_admin_service.Config")
    def test_check_connection_success(self, mock_config, mock_get_engine):
        """Test check_connection when connection is successful."""
        mock_engine = Mock()
        mock_get_engine.return_value = mock_engine
        mock_config.return_value = Mock()

        mock_conn = Mock()
        mock_result = Mock()
        mock_result.scalar.return_value = 1
        mock_conn.execute.return_value = mock_result
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_conn)
        mock_context.__exit__ = Mock(return_value=None)
        mock_engine.connect.return_value = mock_context

        service = DatabaseAdminService("sqlite:///test.db")
        result = service.check_connection()

        assert result is True
        mock_engine.connect.assert_called_once()
        mock_conn.execute.assert_called_once()
        execute_call = mock_conn.execute.call_args[0][0]
        assert str(execute_call) == "SELECT 1"

    @patch("app.services.database_admin_service.db_manager.db_manager.get_engine")
    @patch("app.services.database_admin_service.Config")
    def test_check_connection_failure(self, mock_config, mock_get_engine):
        """Test check_connection when connection fails."""
        mock_engine = Mock()
        mock_get_engine.return_value = mock_engine
        mock_config.return_value = Mock()
        mock_engine.connect.side_effect = ConnectionError("Database unavailable")

        service = DatabaseAdminService("sqlite:///test.db")
        result = service.check_connection()

        assert result is False
        mock_engine.connect.assert_called_once()

    @patch("app.services.database_admin_service.db_manager.db_manager.get_engine")
    @patch("app.services.database_admin_service.Config")
    def test_check_connection_various_exceptions(self, mock_config, mock_get_engine):
        """Test check_connection handles various exception types."""
        mock_engine = Mock()
        mock_get_engine.return_value = mock_engine
        mock_config.return_value = Mock()

        service = DatabaseAdminService("sqlite:///test.db")

        # Test various exception types that should be caught
        exception_types = [
            ImportError("Module not found"),
            AttributeError("Attribute error"),
            RuntimeError("Runtime error"),
            TypeError("Type error"),
            ValueError("Value error"),
            ConnectionError("Connection error"),
            OSError("OS error"),
        ]

        for exc in exception_types:
            mock_engine.connect.side_effect = exc
            result = service.check_connection()
            assert result is False, f"Failed to handle {type(exc).__name__}"

    @patch("app.services.database_admin_service.db_manager.db_manager.get_engine")
    @patch("app.services.database_admin_service.Config")
    def test_check_connection_query_returns_non_one(self, mock_config, mock_get_engine):
        """Test check_connection when query returns unexpected value."""
        mock_engine = Mock()
        mock_get_engine.return_value = mock_engine
        mock_config.return_value = Mock()

        mock_conn = Mock()
        mock_result = Mock()
        mock_result.scalar.return_value = 2  # Unexpected value
        mock_conn.execute.return_value = mock_result
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_conn)
        mock_context.__exit__ = Mock(return_value=None)
        mock_engine.connect.return_value = mock_context

        service = DatabaseAdminService("sqlite:///test.db")
        result = service.check_connection()

        assert result is False
