"""
MCP Server for Basketball Stats Tracker.

This module implements a Model Context Protocol (MCP) server that provides access
to the basketball stats database via a language model API.
"""

import os
import re
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app.config import settings

# Create FastAPI app
app = FastAPI(title="Basketball Stats MCP", description="MCP Server for Basketball Stats Data")

# Get database URL from settings
db_url = settings.DATABASE_URL

# Create engine and session factory
engine = create_engine(db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# API key for simple authentication
API_KEY = os.getenv("MCP_API_KEY")


def verify_api_key(x_api_key: str | None = Header(None)) -> None:
    """Verify the MCP API key from request headers."""
    if not API_KEY:
        raise HTTPException(status_code=500, detail="MCP_API_KEY not configured")
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


# Pydantic models for requests and responses
class MCPRequest(BaseModel):
    """Request model for the MCP Server."""

    query: str = Field(..., description="SQL query or natural language question")
    parameters: dict[str, Any] | None = Field(None, description="Query parameters")


class MCPResponse(BaseModel):
    """Response model for the MCP Server."""

    results: list[dict[str, Any]] = Field([], description="Query results")
    result_schema: dict[str, Any] = Field({}, description="Schema information")
    message: str = Field("", description="Response message")


@app.post("/api/query", response_model=MCPResponse)
async def execute_query(
    request: MCPRequest, _api_key: None = Depends(verify_api_key)
):
    """Execute a read-only SQL query against the database."""
    query = request.query.strip()
    params = request.parameters or {}

    # Only allow SELECT statements and prevent multiple statements
    if not re.match(r"(?i)^select\b", query):
        raise HTTPException(status_code=403, detail="Only SELECT queries are allowed")
    if ";" in query.rstrip(";"):
        raise HTTPException(status_code=400, detail="Multiple statements are not allowed")

    try:
        with SessionLocal() as session:
            # Execute the query
            result = session.execute(text(query), params)

            # Get column names
            if result.keys():
                columns = result.keys()
                # Convert rows to list of dicts
                rows = [dict(zip(columns, row, strict=False)) for row in result.fetchall()]
                schema = dict.fromkeys(columns, "string")  # Basic schema
            else:
                rows = []
                schema = {}

            return MCPResponse(
                results=rows, result_schema=schema, message=f"Query executed successfully. {len(rows)} rows returned."
            )
    except SQLAlchemyError as e:
        raise HTTPException(status_code=400, detail=f"Database error: {str(e)}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing query: {str(e)}") from e


@app.get("/api/tables")
async def get_tables(_api_key: None = Depends(verify_api_key)):
    """Get a list of all tables in the database."""
    try:
        with SessionLocal() as session:
            # SQLite specific way to get tables
            result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
            tables = [row[0] for row in result.fetchall()]
            return {"tables": tables}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting tables: {str(e)}") from e


@app.get("/api/schema/{table}")
async def get_table_schema(table: str, _api_key: None = Depends(verify_api_key)):
    """Get the schema for a specific table."""
    try:
        with SessionLocal() as session:
            # SQLite specific way to get table schema
            result = session.execute(text(f"PRAGMA table_info({table});"))
            columns = [
                {
                    "name": row[1],
                    "type": row[2],
                    "notnull": bool(row[3]),
                    "default": row[4],
                    "primary_key": bool(row[5]),
                }
                for row in result.fetchall()
            ]
            return {"table": table, "columns": columns}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting schema: {str(e)}") from e


@app.get("/api/health")
async def health_check(_api_key: None = Depends(verify_api_key)):
    """Health check endpoint."""
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1;"))
            return {"status": "healthy", "database": "connected"}
    except Exception as e:  # pylint: disable=broad-exception-caught
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}


# Natural language query handling
@app.post("/api/nl_query")
async def natural_language_query(
    request: MCPRequest, _api_key: None = Depends(verify_api_key)
):
    """
    Process a natural language query.
    This is a simple implementation that maps certain types of questions to SQL queries.
    A more sophisticated approach would use a language model for translation.
    """
    query = request.query.lower()
    params = request.parameters or {}

    # Define some simple query mappings
    if "all teams" in query:
        sql_query = "SELECT * FROM teams"
    elif "all players" in query:
        sql_query = "SELECT p.*, t.name as team_name FROM players p JOIN teams t ON p.team_id = t.id"
    elif "all games" in query:
        sql_query = """
        SELECT g.*, t1.name as home_team, t2.name as away_team
        FROM games g
        JOIN teams t1 ON g.playing_team_id = t1.id
        JOIN teams t2 ON g.opponent_team_id = t2.id
        """
    elif "player stats" in query:
        # Extract player name if present
        player_name = None
        import re  # pylint: disable=import-outside-toplevel

        match = re.search(r"player stats for ([a-zA-Z\s]+)", query)
        if match:
            player_name = match.group(1).strip()
            sql_query = """
            SELECT p.name, p.jersey_number, t.name as team_name,
                   pgs.fouls, pgs.total_ftm, pgs.total_fta,
                   pgs.total_2pm, pgs.total_2pa, pgs.total_3pm, pgs.total_3pa
            FROM player_game_stats pgs
            JOIN players p ON pgs.player_id = p.id
            JOIN teams t ON p.team_id = t.id
            WHERE p.name LIKE :player_name
            """
            params = {"player_name": f"%{player_name}%"}
        else:
            sql_query = """
            SELECT p.name, p.jersey_number, t.name as team_name,
                   pgs.fouls, pgs.total_ftm, pgs.total_fta,
                   pgs.total_2pm, pgs.total_2pa, pgs.total_3pm, pgs.total_3pa
            FROM player_game_stats pgs
            JOIN players p ON pgs.player_id = p.id
            JOIN teams t ON p.team_id = t.id
            """
    else:
        # Fallback to a basic query
        sql_query = "SELECT * FROM players LIMIT 10"

    # Execute the generated SQL query
    try:
        with SessionLocal() as session:
            result = session.execute(text(sql_query), params)

            columns = result.keys()
            rows = [dict(zip(columns, row, strict=False)) for row in result.fetchall()]
            schema = dict.fromkeys(columns, "string")

            return MCPResponse(
                results=rows,
                result_schema=schema,
                message=f"Natural language query processed. {len(rows)} rows returned.",
            )
    except SQLAlchemyError as e:
        raise HTTPException(status_code=400, detail=f"Database error: {str(e)}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing natural language query: {str(e)}") from e


def start():
    """Start the server using uvicorn."""
    import uvicorn  # pylint: disable=import-outside-toplevel

    uvicorn.run("app.mcp_server:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    start()
