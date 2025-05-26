# app/schemas/csv_schemas.py
"""
Defines Pydantic models for validating CSV data inputs.

This module contains schemas for:
- Game information (teams, date).
- Individual player statistics rows (jersey, name, fouls, quarter shot strings).
- The overall structure of a game stats CSV import.
"""


from pydantic import BaseModel, Field, field_validator


class GameInfoSchema(BaseModel):
    """
    Pydantic schema for validating the game information part of the CSV.
    """

    HomeTeam: str
    VisitorTeam: str
    Date: str = Field(description="Date can be in YYYY-MM-DD or M/D/YYYY format")

    @field_validator("Date")
    @classmethod
    def validate_date_format(cls, value):
        """Validates that date is in an acceptable format."""
        import re
        # Accept both YYYY-MM-DD and M/D/YYYY formats
        if not re.match(r"^\d{4}-\d{2}-\d{2}$|^\d{1,2}/\d{1,2}/\d{4}$", value):
            raise ValueError("Date must be in YYYY-MM-DD or M/D/YYYY format")
        return value


class PlayerStatsRowSchema(BaseModel):
    """
    Pydantic schema for validating each player's statistics row in the CSV.
    """

    TeamName: str
    PlayerJersey: str = Field(description="Player jersey number as string to handle 0 vs 00")
    PlayerName: str
    Fouls: int | None = Field(default=0, ge=0, description="Fouls must be non-negative")
    QT1Shots: str = ""
    QT2Shots: str = ""
    QT3Shots: str = ""
    QT4Shots: str = ""

    @classmethod
    @field_validator("Fouls")
    def check_fouls_non_negative(cls, value, info):
        """Validates that fouls are non-negative."""
        if value is not None and value < 0:
            field_name = info.field_name
            raise ValueError("Input should be greater than or equal to 0", field_name)
        return value
        
    @classmethod
    @field_validator("PlayerJersey")
    def validate_jersey_number(cls, value):
        """Validates that jersey number is a valid string."""
        if not value or not value.strip():
            raise ValueError("Jersey number cannot be empty")
        # Allow any string that represents a valid jersey number
        return value.strip()


class GameStatsCSVInputSchema(BaseModel):
    """
    Pydantic schema for validating the entire parsed CSV structure for game stats.
    This model assumes that the CSV parsing logic will transform the raw CSV
    into a structure that fits this model (e.g., a dictionary with 'game_info'
    and 'player_stats' keys).
    """

    game_info: GameInfoSchema
    player_stats: list[PlayerStatsRowSchema]

    @field_validator("player_stats")
    @classmethod
    def validate_player_stats_not_empty(cls, value):
        """Validates that player_stats list is not empty."""
        if not value:
            raise ValueError("List should have at least 1 item")
        return value

    class Config:
        """Pydantic configuration for the schema."""

        arbitrary_types_allowed = True  # Allow arbitrary types for better type flexibility


# Example of how this might be populated by a CSV parser:
# parsed_data = {
#     "game_info": {
#         "PlayingTeam": "Team A",
#         "OpponentTeam": "Team B",
#         "Date": "2024-05-15"
#     },
#     "player_stats": [
#         {
#             "TeamName": "Team A",
#             "PlayerJersey": 10,
#             "PlayerName": "Player One",
#             "Fouls": 2,
#             "QT1Shots": "22-1x",
#             "QT2Shots": "3/2",
#             "QT3Shots": "11",
#             "QT4Shots": ""
#         },
#         # ... more players
#     ]
# }
# validated_input = GameStatsCSVInputSchema(**parsed_data)
