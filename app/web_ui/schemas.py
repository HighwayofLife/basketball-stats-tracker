# app/web_ui/schemas.py

"""Pydantic schemas for the Basketball Stats Tracker API."""

from typing import Any

from pydantic import BaseModel, Field


class GameSummary(BaseModel):
    """Basic information about a basketball game."""

    id: int
    date: str  # Using string since that's what the model uses
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
    top_player: dict[str, Any] | None = None


class BoxScoreResponse(BaseModel):
    """Full box score for a basketball game."""

    game_id: int
    game_date: str  # Using string since that's what the model uses
    home_team: TeamStats
    away_team: TeamStats


# Live Game Entry Schemas


class GameCreateRequest(BaseModel):
    """Request schema for creating a new game."""

    date: str = Field(..., description="Game date in YYYY-MM-DD format")
    home_team_id: int
    away_team_id: int
    location: str | None = None
    scheduled_time: str | None = Field(None, description="Scheduled time in HH:MM format")
    notes: str | None = None


class GameStartRequest(BaseModel):
    """Request schema for starting a game."""

    home_starters: list[int] = Field(
        default=..., min_length=5, max_length=5, description="List of 5 home team starter player IDs"
    )
    away_starters: list[int] = Field(
        default=..., min_length=5, max_length=5, description="List of 5 away team starter player IDs"
    )


class RecordShotRequest(BaseModel):
    """Request schema for recording a shot."""

    player_id: int
    shot_type: str = Field(..., pattern="^(2pt|3pt|ft)$", description="Type of shot: 2pt, 3pt, or ft")
    made: bool
    quarter: int | None = Field(None, ge=1, le=4)
    assisted_by: int | None = None


class RecordFoulRequest(BaseModel):
    """Request schema for recording a foul."""

    player_id: int
    foul_type: str = Field("personal", pattern="^(personal|technical|flagrant)$")
    quarter: int | None = Field(None, ge=1, le=4)


class SubstitutionRequest(BaseModel):
    """Request schema for player substitutions."""

    team_id: int
    players_out: list[int] = Field(..., min_length=1, description="Players going out")
    players_in: list[int] = Field(..., min_length=1, description="Players coming in")


class ActivePlayer(BaseModel):
    """Schema for an active player in the game."""

    id: int
    name: str
    jersey_number: str
    position: str | None = None
    is_starter: bool


class GameStateInfo(BaseModel):
    """Schema for game state information."""

    game_id: int
    current_quarter: int
    is_live: bool
    is_final: bool
    home_score: int
    away_score: int
    home_timeouts: int
    away_timeouts: int


class GameEventInfo(BaseModel):
    """Schema for game event information."""

    id: int
    type: str
    player_id: int | None = None
    team_id: int | None = None
    quarter: int
    timestamp: str
    details: dict[str, Any] | None = None


class GameStateResponse(BaseModel):
    """Response schema for live game state."""

    game_state: GameStateInfo
    active_players: dict[str, list[ActivePlayer]]
    recent_events: list[GameEventInfo]


class GameEventResponse(BaseModel):
    """Response schema for game events."""

    event_id: int
    player_id: int | None = None
    team_id: int | None = None
    event_type: str
    quarter: int
    details: dict[str, Any]


# Team Management Schemas


class TeamCreateRequest(BaseModel):
    """Request schema for creating a new team."""

    name: str = Field(..., min_length=1, max_length=100, description="Team name")
    display_name: str | None = Field(None, min_length=1, max_length=100, description="Display name (optional)")


class TeamUpdateRequest(BaseModel):
    """Request schema for updating a team."""

    name: str | None = Field(None, min_length=1, max_length=100, description="Team name (for CSV imports)")
    display_name: str | None = Field(None, min_length=1, max_length=100, description="Display name")


class TeamResponse(BaseModel):
    """Response schema for team information."""

    id: int
    name: str
    display_name: str | None = None
    player_count: int = 0


class TeamDetailResponse(BaseModel):
    """Detailed response schema for team information."""

    id: int
    name: str
    display_name: str | None = None
    players: list["PlayerResponse"]


# Player Management Schemas


class PlayerCreateRequest(BaseModel):
    """Request schema for creating a new player."""

    name: str = Field(..., min_length=1, max_length=100, description="Player name")
    team_id: int
    jersey_number: str = Field(..., min_length=1, max_length=10, description="Jersey number (e.g., '0', '00', '23')")
    position: str | None = Field(None, pattern="^(PG|SG|SF|PF|C)$", description="Position: PG, SG, SF, PF, or C")
    height: int | None = Field(None, ge=48, le=96, description="Height in inches")
    weight: int | None = Field(None, ge=100, le=400, description="Weight in pounds")
    year: str | None = Field(None, description="Academic year (e.g., Freshman, Junior)")


class PlayerUpdateRequest(BaseModel):
    """Request schema for updating a player."""

    name: str | None = Field(None, min_length=1, max_length=100, description="Player name")
    team_id: int | None = None
    jersey_number: str | None = Field(
        None, min_length=1, max_length=10, description="Jersey number (e.g., '0', '00', '23')"
    )
    position: str | None = Field(None, pattern="^(PG|SG|SF|PF|C)$", description="Position: PG, SG, SF, PF, or C")
    height: int | None = Field(None, ge=48, le=96, description="Height in inches")
    weight: int | None = Field(None, ge=100, le=400, description="Weight in pounds")
    year: str | None = Field(None, description="Academic year (e.g., Freshman, Junior)")
    is_active: bool | None = None


class PlayerResponse(BaseModel):
    """Response schema for player information."""

    id: int
    name: str
    team_id: int
    team_name: str
    jersey_number: str
    position: str | None = None
    height: int | None = None
    weight: int | None = None
    year: str | None = None
    is_active: bool = True


# Season Statistics Schemas


class PlayerSeasonStatsResponse(BaseModel):
    """Response schema for player season statistics."""

    player_id: int
    player_name: str
    team_name: str
    season: str
    games_played: int
    total_points: int
    ppg: float  # Points per game
    total_fouls: int
    fpg: float  # Fouls per game
    ftm: int
    fta: int
    ft_pct: float | None
    fg2m: int
    fg2a: int
    fg2_pct: float | None
    fg3m: int
    fg3a: int
    fg3_pct: float | None
    fgm: int  # Total field goals made (2P + 3P)
    fga: int  # Total field goals attempted
    fg_pct: float | None  # Overall field goal percentage
    efg_pct: float | None  # Effective field goal percentage


class TeamSeasonStatsResponse(BaseModel):
    """Response schema for team season statistics."""

    team_id: int
    team_name: str
    season: str
    games_played: int
    wins: int
    losses: int
    win_pct: float
    ppg: float  # Points per game
    opp_ppg: float  # Opponent points per game
    point_diff: float  # Average point differential
    ftm: int
    fta: int
    ft_pct: float | None
    fg2m: int
    fg2a: int
    fg2_pct: float | None
    fg3m: int
    fg3a: int
    fg3_pct: float | None
    fgm: int
    fga: int
    fg_pct: float | None
    efg_pct: float | None


class PlayerRankingResponse(BaseModel):
    """Response schema for player rankings/leaderboards."""

    rank: int
    player_id: int
    player_name: str
    team_name: str
    value: float
    games_played: int


class TeamStandingsResponse(BaseModel):
    """Response schema for team standings."""

    rank: int
    team_id: int
    team_name: str
    wins: int
    losses: int
    win_pct: float
    games_back: float | None
    ppg: float
    opp_ppg: float
    point_diff: float
    streak: str  # e.g., "W3", "L2"
    last_10: str  # e.g., "7-3"


class SeasonSummaryResponse(BaseModel):
    """Response schema for season summary information."""

    season: str
    total_games: int
    top_scorers: list[PlayerRankingResponse]
    team_standings: list[TeamStandingsResponse]
    league_leaders: dict[str, list[PlayerRankingResponse]]  # Category -> Rankings


# Forward reference for circular dependency
TeamDetailResponse.model_rebuild()
