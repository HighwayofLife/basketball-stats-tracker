"""
Report generation module for basketball statistics.

This module provides functionality for generating various statistical reports
including box scores and game summaries.
"""
# mypy: disable-error-code="operator"
from sqlalchemy.orm import Session

from app.data_access.crud import crud_game, crud_player, crud_player_game_stats, crud_player_quarter_stats, crud_team


class ReportGenerator:
    """
    Generates statistical reports for basketball games.

    Handles the creation of box scores and game summary reports based on player
    and team statistics stored in the database.
    """
    def __init__(self, db_session: Session, stats_calculator_module):
        self.db_session = db_session
        self.stats_calculator = stats_calculator_module

    def _fetch_game_and_teams(self, game_id: int) -> tuple:
        """
        Fetch game and team data for a given game ID.

        Args:
            game_id: ID of the game

        Returns:
            Tuple of (game, playing_team, opponent_team)
            Any of these may be None if not found
        """
        game = crud_game.get_game_by_id(self.db_session, game_id)
        if not game:
            return None, None, None

        playing_team = crud_team.get_team_by_id(self.db_session, game.playing_team_id)
        opponent_team = crud_team.get_team_by_id(self.db_session, game.opponent_team_id)

        return game, playing_team, opponent_team

    def _initialize_team_totals(self) -> dict:
        """
        Initialize the team totals dictionary with zero values.

        Returns:
            Dictionary with team total stats initialized to zero
        """
        return {
            "points": 0,
            "ftm": 0,
            "fta": 0,
            "fg2m": 0,
            "fg2a": 0,
            "fg3m": 0,
            "fg3a": 0,
            "fouls": 0,
            "total_fgm": 0,
            "total_fga": 0,
        }

    def _get_team_name(self, player, playing_team, opponent_team) -> str:
        """
        Determine the team name for a player.

        Args:
            player: Player object
            playing_team: Team object for the playing team
            opponent_team: Team object for the opponent team

        Returns:
            String with the team name
        """
        if player.team_id == playing_team.id:
            return playing_team.name
        elif player.team_id == opponent_team.id:
            return opponent_team.name
        else:
            return "Unknown Team"

    def _calculate_player_box_score(
        self, player, pgs, quarter_stats, playing_team, opponent_team
    ) -> tuple[dict, int, int]:
        """
        Calculate box score statistics for a single player.

        Args:
            player: Player object
            pgs: Player game stats object
            quarter_stats: Quarter stats for the player
            playing_team: Team object for the playing team
            opponent_team: Team object for the opponent team

        Returns:
            Tuple of (player_box_score, total_fgm, total_fga)
        """
        # Determine the team name
        team_name = self._get_team_name(player, playing_team, opponent_team)

        # Initialize stats for this player
        player_box_score = {
            "name": player.name,
            "jersey": player.jersey_number,
            "team": team_name,
            "fouls": pgs.fouls,
            "ftm": 0,
            "fta": 0,
            "ft_pct": None,
            "fg2m": 0,
            "fg2a": 0,
            "fg2_pct": None,
            "fg3m": 0,
            "fg3a": 0,
            "fg3_pct": None,
            "points": 0,
            "efg": None,
            "ts_pct": None,
        }

        # Aggregate stats from all quarters
        for qs in quarter_stats:
            # Use explicit type conversion to int to avoid mypy "object + int" errors
            ftm_value = int(qs.ftm) if qs.ftm is not None else 0
            fta_value = int(qs.fta) if qs.fta is not None else 0
            fg2m_value = int(qs.fg2m) if qs.fg2m is not None else 0
            fg2a_value = int(qs.fg2a) if qs.fg2a is not None else 0
            fg3m_value = int(qs.fg3m) if qs.fg3m is not None else 0
            fg3a_value = int(qs.fg3a) if qs.fg3a is not None else 0

            player_box_score["ftm"] += ftm_value
            player_box_score["fta"] += fta_value
            player_box_score["fg2m"] += fg2m_value
            player_box_score["fg2a"] += fg2a_value
            player_box_score["fg3m"] += fg3m_value
            player_box_score["fg3a"] += fg3a_value

        # Calculate percentages and points
        player_box_score["ft_pct"] = self.stats_calculator.calculate_percentage(
            player_box_score["ftm"], player_box_score["fta"]
        )
        player_box_score["fg2_pct"] = self.stats_calculator.calculate_percentage(
            player_box_score["fg2m"], player_box_score["fg2a"]
        )
        player_box_score["fg3_pct"] = self.stats_calculator.calculate_percentage(
            player_box_score["fg3m"], player_box_score["fg3a"]
        )

        player_box_score["points"] = self.stats_calculator.calculate_points(
            player_box_score["ftm"], player_box_score["fg2m"], player_box_score["fg3m"]
        )

        # Calculate advanced stats
        # Convert values to int to handle MyPy type checking
        fg2m_int = player_box_score["fg2m"]
        fg3m_int = player_box_score["fg3m"]
        fg2a_int = player_box_score["fg2a"]
        fg3a_int = player_box_score["fg3a"]

        total_fgm = fg2m_int + fg3m_int  # type: ignore
        total_fga = fg2a_int + fg3a_int  # type: ignore

        player_box_score["efg"] = self.stats_calculator.calculate_efg(
            total_fgm, player_box_score["fg3m"], total_fga
        )

        player_box_score["ts_pct"] = self.stats_calculator.calculate_ts(
            player_box_score["points"], total_fga, player_box_score["fta"]
        )

        return player_box_score, total_fgm, total_fga

    def _update_team_totals(
        self, team_totals: dict, player_box_score: dict,
        total_fgm: int, total_fga: int, player_team_id, playing_team_id
    ) -> None:
        """
        Update team totals with player stats if the player is on the playing team.

        Args:
            team_totals: Dictionary with team stats
            player_box_score: Dictionary with player box score
            total_fgm: Total field goals made
            total_fga: Total field goals attempted
            player_team_id: Team ID of the player
            playing_team_id: Team ID of the playing team
        """
        if player_team_id == playing_team_id:
            team_totals["points"] += player_box_score["points"]
            team_totals["ftm"] += player_box_score["ftm"]
            team_totals["fta"] += player_box_score["fta"]
            team_totals["fg2m"] += player_box_score["fg2m"]
            team_totals["fg2a"] += player_box_score["fg2a"]
            team_totals["fg3m"] += player_box_score["fg3m"]
            team_totals["fg3a"] += player_box_score["fg3a"]
            team_totals["fouls"] += player_box_score["fouls"]
            team_totals["total_fgm"] += total_fgm
            team_totals["total_fga"] += total_fga

    def _calculate_team_percentages(self, team_totals: dict) -> None:
        """
        Calculate percentage statistics for the team.

        Args:
            team_totals: Dictionary with team stats to update with percentages
        """
        team_totals["ft_pct"] = self.stats_calculator.calculate_percentage(
            team_totals["ftm"], team_totals["fta"]
        )
        team_totals["fg2_pct"] = self.stats_calculator.calculate_percentage(
            team_totals["fg2m"], team_totals["fg2a"]
        )
        team_totals["fg3_pct"] = self.stats_calculator.calculate_percentage(
            team_totals["fg3m"], team_totals["fg3a"]
        )
        team_totals["efg"] = self.stats_calculator.calculate_efg(
            team_totals["total_fgm"], team_totals["fg3m"], team_totals["total_fga"]
        )
        team_totals["ts_pct"] = self.stats_calculator.calculate_ts(
            team_totals["points"], team_totals["total_fga"], team_totals["fta"]
        )

    def _create_game_summary(self, game, playing_team, opponent_team, team_totals: dict) -> dict:
        """
        Create the game summary dictionary.

        Args:
            game: Game object
            playing_team: Team object for the playing team
            opponent_team: Team object for the opponent team
            team_totals: Dictionary with team stats

        Returns:
            Dictionary with game summary information
        """
        return {
            "game_id": game.id,
            "date": game.date,
            "playing_team": playing_team.name,
            "opponent_team": opponent_team.name,
            "team_points": team_totals["points"],
            "team_fouls": team_totals["fouls"],
            "team_ft_pct": team_totals["ft_pct"],
            "team_fg2_pct": team_totals["fg2_pct"],
            "team_fg3_pct": team_totals["fg3_pct"],
            "team_efg": team_totals["efg"],
            "team_ts_pct": team_totals["ts_pct"],
        }

    def get_game_box_score_data(self, game_id: int) -> tuple[list, dict]:
        """
        Generate a box score report for a game.

        Args:
            game_id: ID of the game to generate report for.

        Returns:
            A tuple containing:
            - List of player stats dictionaries (box score data)
            - Game summary dictionary (team totals, game information)
        """
        # Fetch game and team data
        game, playing_team, opponent_team = self._fetch_game_and_teams(game_id)
        if not game:
            raise ValueError(f"Game not found with id: {game_id}")
        if not playing_team or not opponent_team:
            raise ValueError(f"Teams not found for game with id: {game_id}")

        # Fetch all player game stats for this game
        player_game_stats = crud_player_game_stats.get_player_game_stats_by_game(self.db_session, game_id)

        player_stats_list = []
        team_totals = self._initialize_team_totals()

        for pgs in player_game_stats:
            # Get the player
            player = crud_player.get_player_by_id(self.db_session, pgs.player_id)
            if not player:
                continue

            # Get all quarter stats for this player in this game
            quarter_stats = crud_player_quarter_stats.get_player_quarter_stats(self.db_session, pgs.id)

            # Calculate player box score
            player_box_score, total_fgm, total_fga = self._calculate_player_box_score(
                player, pgs, quarter_stats, playing_team, opponent_team
            )

            # Add player to report list
            player_stats_list.append(player_box_score)

            # Update team totals if applicable
            self._update_team_totals(
                team_totals, player_box_score, total_fgm, total_fga,
                player.team_id, playing_team.id
            )

        # Calculate team percentage stats
        self._calculate_team_percentages(team_totals)

        # Create game summary
        game_summary = self._create_game_summary(game, playing_team, opponent_team, team_totals)

        # Sort players by points (descending) for better display
        player_stats_list.sort(key=lambda x: x["points"], reverse=True)  # type: ignore

        return player_stats_list, game_summary
