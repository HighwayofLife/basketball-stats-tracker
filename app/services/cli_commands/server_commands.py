"""Server-related CLI command handlers."""

import logging

import typer
import uvicorn


class ServerCommands:
    """Handles server-related CLI commands."""

    @staticmethod
    def start_mcp_server() -> None:
        """
        Start the Model Context Protocol (MCP) server for SQL queries and natural language processing.
        This server provides API access to the basketball stats database via HTTP endpoints.
        """
        typer.echo("Starting MCP Server...")
        # pylint: disable=import-outside-toplevel
        from app.mcp_server import start

        start()

    @staticmethod
    def start_web_server(host: str = "127.0.0.1", port: int = 8000, reload: bool = False) -> None:
        """
        Start the web UI server with FastAPI.

        Args:
            host: The host IP to bind the server to
            port: The port to run the server on
            reload: Whether to reload the server on code changes (development only)
        """
        logging.info("Starting web UI server on %s:%d", host, port)

        # Start the server
        uvicorn.run(
            "app.web_ui.app:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info",
        )
