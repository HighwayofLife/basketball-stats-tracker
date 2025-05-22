# app/web_ui/schemas.py

"""Pydantic schemas for the Basketball Stats Tracker API."""

from datetime import date
from typing import Any

from pydantic import BaseModel


class GameSummary(BaseModel):
    """Basic information about a basketball game."""

    id: int
    date: date
    home_team: str
    home_team_id: int
    away_team: str
    away_team_id: int
    home_score: int
    away_score: int


class PlayerStats(BaseModel):
    """Player statistics for a game."""

    player_id: int
    name: str
    stats: dict[str, Any]


class TeamStats(BaseModel):
    """Team statistics for a game."""

    team_id: int
    name: str
    score: int
    stats: dict[str, Any]
    players: list[PlayerStats]


class BoxScoreResponse(BaseModel):
    """Full box score for a basketball game."""

    game_id: int
    game_date: date
    home_team: TeamStats
    away_team: TeamStats
