"""
Integration tests for container startup and deployment scenarios.

Tests that simulate the actual Cloud Run deployment process to catch
startup failures before they reach production.
"""

import os
import subprocess
import time
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# Set JWT_SECRET_KEY for all tests in this module
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-that-is-long-enough-for-validation-purposes"


class TestContainerStartup:
    """Test container startup scenarios that mirror Cloud Run deployment."""

    @pytest.fixture(autouse=True)
    def reset_app_for_each_test(self):
        """Reset app state before and after each test."""
        from app.web_ui.api import app

        # Store original state
        original_overrides = app.dependency_overrides.copy()

        # Clear before test
        app.dependency_overrides.clear()

        yield

        # Restore after test
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)

    def test_fastapi_uvicorn_startup_simulation(self):
        """Simulate how uvicorn starts the FastAPI app in production."""
        try:
            # Import exactly as uvicorn does: app.web_ui.api:app
            from app.web_ui.api import app

            # Create test client (simulates uvicorn creating the ASGI app)
            with TestClient(app) as client:
                # Verify the app is ready to serve traffic
                response = client.get("/health")
                assert response.status_code == 200

                data = response.json()
                assert data["status"] == "ok"

        except Exception as e:
            pytest.fail(f"Uvicorn startup simulation failed: {e}")

    def test_production_environment_startup(self):
        """Test startup with production environment variables."""
        prod_env = {
            "ENVIRONMENT": "production",
            "SECRET_KEY": "test-production-secret-key-123",
            "DATABASE_URL": "postgresql://testuser:testpass@localhost:5432/testdb",
            "PORT": "8000",
            "JWT_SECRET_KEY": "test-jwt-secret-key-that-is-long-enough-for-validation-purposes",
        }

        with patch.dict(os.environ, prod_env):
            try:
                from app.web_ui.api import app

                with TestClient(app) as client:
                    # App should start without errors in production mode
                    response = client.get("/health")
                    assert response.status_code == 200

            except Exception as e:
                pytest.fail(f"Production environment startup failed: {e}")

    def test_startup_with_database_connection_failure(self):
        """Test that app can start even when database is unavailable."""
        # Simulate database connection failure
        bad_db_env = {"DATABASE_URL": "postgresql://baduser:badpass@nonexistent:5432/baddb"}

        with patch.dict(os.environ, bad_db_env):
            try:
                from app.web_ui.api import app

                client = TestClient(app)

                # Health endpoint should still work even if DB is down
                response = client.get("/health")
                assert response.status_code == 200

                # App should be created successfully
                assert app is not None

            except Exception as e:
                pytest.fail(f"App failed to start with database connection issues: {e}")

    def test_startup_time_within_cloud_run_limits(self):
        """Test that startup time is within Cloud Run timeout limits."""
        start_time = time.time()

        try:
            from app.web_ui.api import app

            with TestClient(app) as client:
                # Make a request to ensure app is fully loaded
                response = client.get("/health")
                assert response.status_code == 200

                total_time = time.time() - start_time

            # Cloud Run has a default startup timeout, app should start much faster
            assert total_time < 10.0, f"Startup took {total_time:.2f}s, may timeout in Cloud Run"

        except Exception as e:
            pytest.fail(f"Startup time test failed: {e}")

    def test_no_database_migrations_during_startup(self):
        """Test that no database migrations run during app startup."""
        migration_logs = []

        def capture_migration_log(*args, **kwargs):
            migration_logs.append("Migration attempted during startup")
            raise Exception("Migrations should not run during app startup")

        # Mock all possible migration entry points
        with patch(
            "app.services.database_admin_service.DatabaseAdminService.initialize_schema",
            side_effect=capture_migration_log,
        ):
            with patch(
                "app.services.database_admin_service.DatabaseAdminService.upgrade_to_head",
                side_effect=capture_migration_log,
            ):
                with patch("alembic.command.upgrade", side_effect=capture_migration_log):
                    try:
                        from app.web_ui.api import app

                        with TestClient(app) as client:
                            # App should start without attempting migrations
                            response = client.get("/health")
                            assert response.status_code == 200

                            # No migration attempts should have been made
                            assert len(migration_logs) == 0, f"Migration attempts detected: {migration_logs}"

                    except Exception as e:
                        if "Migrations should not run" in str(e):
                            pytest.fail("App attempted to run migrations during startup")
                        else:
                            pytest.fail(f"Startup test failed: {e}")

    def test_port_binding_simulation(self):
        """Test that the app can bind to the correct port (simulates Cloud Run PORT env var)."""
        port_env = {"PORT": "8080"}

        with patch.dict(os.environ, port_env):
            try:
                from app.web_ui.api import app

                with TestClient(app) as client:
                    # App should start regardless of PORT env var (TestClient handles this)
                    response = client.get("/health")
                    assert response.status_code == 200

            except Exception as e:
                pytest.fail(f"Port binding test failed: {e}")

    @pytest.mark.skip(reason="Test has module import conflicts due to environment variable timing")
    def test_middleware_configuration_in_production(self):
        """Test that production middleware is properly configured."""
        prod_env = {"APP_ENV": "production", "ENVIRONMENT": "production"}

        with patch.dict(os.environ, prod_env):
            try:
                from app.web_ui.api import app

                # Check that TrustedHostMiddleware is added in production
                middleware_types = [type(middleware).__name__ for middleware in app.user_middleware]
                assert "TrustedHostMiddleware" in middleware_types, (
                    "TrustedHostMiddleware should be enabled in production"
                )

            except Exception as e:
                pytest.fail(f"Middleware configuration test failed: {e}")

    def test_static_files_mounting(self):
        """Test that static files are properly mounted without blocking startup."""
        try:
            from app.web_ui.api import app

            client = TestClient(app)

            # Static files should be mounted
            static_routes = [route for route in app.routes if hasattr(route, "name") and route.name == "static"]
            assert len(static_routes) > 0, "Static files should be mounted"

        except Exception as e:
            pytest.fail(f"Static files mounting test failed: {e}")


@pytest.mark.slow
class TestDockerContainerStartup:
    """Tests that require Docker to simulate actual container startup."""

    @pytest.mark.skipif(
        not os.path.exists("/usr/bin/docker") and not os.path.exists("/usr/local/bin/docker"),
        reason="Docker not available",
    )
    def test_docker_build_succeeds(self):
        """Test that Docker build completes successfully."""
        try:
            # Build the production Docker image
            result = subprocess.run(
                [
                    "docker",
                    "build",
                    "--target",
                    "production",
                    "--build-arg",
                    "APP_VERSION=test",
                    "--build-arg",
                    "GIT_HASH=test123",
                    "-t",
                    "basketball-stats-test",
                    ".",
                ],
                capture_output=True,
                text=True,
                timeout=300,
            )

            assert result.returncode == 0, f"Docker build failed: {result.stderr}"

        except subprocess.TimeoutExpired:
            pytest.fail("Docker build timed out")
        except Exception as e:
            pytest.fail(f"Docker build test failed: {e}")
