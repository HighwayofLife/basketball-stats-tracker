# app/schemas/csv_schemas.py
"""
Defines Pydantic models for validating CSV data inputs.

This module contains schemas for:
- Game information (teams, date).
- Individual player statistics rows (jersey, name, fouls, quarter shot strings).
- The overall structure of a game stats CSV import.
"""
from pydantic import BaseModel, field_validator


class GameInfoSchema(BaseModel):
    """
    Pydantic schema for validating the game information part of the CSV.
    """
    PlayingTeam: str
    OpponentTeam: str
    Date: str # Expects YYYY-MM-DD

    @classmethod
    @field_validator('Date')
    def validate_date_format(cls, value):
        """Validates that the date string is in YYYY-MM-DD format."""
        # Add more sophisticated date validation if needed
        # For now, just checking length and basic structure
        if not (len(value) == 10 and value[4] == '-' and value[7] == '-'):
            raise ValueError('Date must be in YYYY-MM-DD format')
        return value

class PlayerStatsRowSchema(BaseModel):
    """
    Pydantic schema for validating each player's statistics row in the CSV.
    """
    TeamName: str
    PlayerJersey: int
    PlayerName: str
    Fouls: int
    QT1Shots: str = ""
    QT2Shots: str = ""
    QT3Shots: str = ""
    QT4Shots: str = ""

    @classmethod
    @field_validator('PlayerJersey', 'Fouls')
    def check_non_negative(cls, value):
        """Validates that jersey number and fouls are non-negative."""
        if value < 0:
            raise ValueError('Jersey number and Fouls must be non-negative')
        return value

class GameStatsCSVInputSchema(BaseModel):
    """
    Pydantic schema for validating the entire parsed CSV structure for game stats.
    This model assumes that the CSV parsing logic will transform the raw CSV
    into a structure that fits this model (e.g., a dictionary with 'game_info'
    and 'player_stats' keys).
    """
    game_info: GameInfoSchema
    player_stats: list[PlayerStatsRowSchema]

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
