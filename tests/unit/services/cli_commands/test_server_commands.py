"""Unit tests for server-related CLI command handlers."""

from unittest.mock import patch

from app.services.cli_commands.server_commands import ServerCommands


class TestServerCommands:
    """Test server-related CLI commands."""

    @patch("app.mcp_server.start")
    def test_start_mcp_server(self, mock_start, capsys):
        """Test MCP server start command."""
        ServerCommands.start_mcp_server()

        mock_start.assert_called_once()
        captured = capsys.readouterr()
        assert "Starting MCP Server..." in captured.out

    @patch("app.services.cli_commands.server_commands.uvicorn.run")
    def test_start_web_server_default(self, mock_uvicorn):
        """Test web server start with default parameters."""
        ServerCommands.start_web_server()

        mock_uvicorn.assert_called_once_with(
            "app.web_ui.app:app",
            host="127.0.0.1",
            port=8000,
            reload=False,
            log_level="info",
        )

    @patch("app.services.cli_commands.server_commands.uvicorn.run")
    def test_start_web_server_custom_params(self, mock_uvicorn):
        """Test web server start with custom parameters."""
        ServerCommands.start_web_server(host="0.0.0.0", port=8080, reload=True)

        mock_uvicorn.assert_called_once_with(
            "app.web_ui.app:app",
            host="0.0.0.0",
            port=8080,
            reload=True,
            log_level="info",
        )
