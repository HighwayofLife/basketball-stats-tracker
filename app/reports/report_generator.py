"""
Report generation module for basketball statistics.

This module provides functionality for generating various statistical reports
including:
- Box scores and game summaries (traditional statistics)
- Player performance reports (detailed per-player analysis)
- Team efficiency reports (offensive efficiency metrics)
- Scoring analysis reports (breakdown of scoring patterns)
- Game flow reports (quarter-by-quarter momentum analysis)

Each report type offers different insights for coaches, players, and team managers.
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
            # New fields for additional statistics
            "ppsa": None,
            "scoring_distribution": {"ft_pct": None, "fg2_pct": None, "fg3_pct": None},
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
            quarter_stats: Quarter stats for the player (list or dict)
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
            # New fields for additional statistics
            "ppsa": None,
            "scoring_distribution": {"ft_pct": None, "fg2_pct": None, "fg3_pct": None},
        }

        # Aggregate stats from all quarters
        # quarter_stats could be a list or a dictionary depending on the test scenario
        quarter_stats_list = quarter_stats.values() if isinstance(quarter_stats, dict) else quarter_stats

        for qs in quarter_stats_list:
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

        player_box_score["efg"] = self.stats_calculator.calculate_efg(total_fgm, player_box_score["fg3m"], total_fga)

        player_box_score["ts_pct"] = self.stats_calculator.calculate_ts(
            player_box_score["points"], total_fga, player_box_score["fta"]
        )

        # Calculate PPSA (Points Per Shot Attempt)
        player_box_score["ppsa"] = self.stats_calculator.calculate_ppsa(
            player_box_score["points"], total_fga, player_box_score["fta"]
        )

        # Calculate scoring distribution
        ft_points = player_box_score["ftm"]
        fg2_points = player_box_score["fg2m"] * 2
        fg3_points = player_box_score["fg3m"] * 3
        player_box_score["scoring_distribution"] = self.stats_calculator.calculate_scoring_distribution(
            ft_points, fg2_points, fg3_points
        )

        return player_box_score, total_fgm, total_fga

    def _update_team_totals(
        self, team_totals: dict, player_box_score: dict, total_fgm: int, total_fga: int, player_team_id, playing_team_id
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
        team_totals["ft_pct"] = self.stats_calculator.calculate_percentage(team_totals["ftm"], team_totals["fta"])
        team_totals["fg2_pct"] = self.stats_calculator.calculate_percentage(team_totals["fg2m"], team_totals["fg2a"])
        team_totals["fg3_pct"] = self.stats_calculator.calculate_percentage(team_totals["fg3m"], team_totals["fg3a"])
        team_totals["efg"] = self.stats_calculator.calculate_efg(
            team_totals["total_fgm"], team_totals["fg3m"], team_totals["total_fga"]
        )
        team_totals["ts_pct"] = self.stats_calculator.calculate_ts(
            team_totals["points"], team_totals["total_fga"], team_totals["fta"]
        )

        # Calculate PPSA for team
        team_totals["ppsa"] = self.stats_calculator.calculate_ppsa(
            team_totals["points"], team_totals["total_fga"], team_totals["fta"]
        )

        # Calculate scoring distribution for team
        ft_points = team_totals["ftm"]
        fg2_points = team_totals["fg2m"] * 2
        fg3_points = team_totals["fg3m"] * 3
        team_totals["scoring_distribution"] = self.stats_calculator.calculate_scoring_distribution(
            ft_points, fg2_points, fg3_points
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
        # Format date as string for display
        date_str = game.date.strftime("%Y-%m-%d") if hasattr(game.date, "strftime") else str(game.date)

        return {
            "game_id": game.id,
            "date": date_str,
            "playing_team": playing_team.name,
            "opponent_team": opponent_team.name,
            "team_points": team_totals["points"],
            "team_fouls": team_totals["fouls"],
            "team_ft_pct": team_totals["ft_pct"],
            "team_fg2_pct": team_totals["fg2_pct"],
            "team_fg3_pct": team_totals["fg3_pct"],
            "team_efg": team_totals["efg"],
            "team_ts_pct": team_totals["ts_pct"],
            "team_ppsa": team_totals["ppsa"],
            "team_scoring_distribution": team_totals["scoring_distribution"],
        }

    def _handle_missing_quarter_data(self, quarter_stats, quarters=4):
        """
        Ensure quarter data is complete by filling in missing quarters with zeroes.

        Some games might have missing quarter data if a player didn't play in that quarter
        or if the data wasn't recorded. This method ensures all quarters have entries
        with at least zero values.

        Args:
            quarter_stats: List of PlayerQuarterStats objects or dictionary keyed by quarter number
            quarters: Number of quarters to ensure are present (default 4)

        Returns:
            Dictionary mapping quarter numbers to either the actual stat object
            or a dummy object with zeroed stats
        """
        # Create a dictionary to map quarter numbers to stats
        quarter_map = {}

        # If quarter_stats is already a dictionary with int keys (from tests)
        if isinstance(quarter_stats, dict) and all(isinstance(k, int) for k in quarter_stats):
            return quarter_stats

        # Fill in with actual data
        for qs in quarter_stats:
            quarter_map[qs.quarter] = qs

        # Create dummy stats for missing quarters
        for q in range(1, quarters + 1):
            if q not in quarter_map:
                # Create a dummy stat object with zero values
                dummy_stat = type(
                    "DummyQuarterStat",
                    (),
                    {"quarter": q, "ftm": 0, "fta": 0, "fg2m": 0, "fg2a": 0, "fg3m": 0, "fg3a": 0},
                )
                quarter_map[q] = dummy_stat

        return quarter_map

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
            quarter_stats = self._handle_missing_quarter_data(quarter_stats)
            player_box_score, total_fgm, total_fga = self._calculate_player_box_score(
                player, pgs, quarter_stats, playing_team, opponent_team
            )

            # Add player to report list
            player_stats_list.append(player_box_score)

            # Update team totals if applicable
            self._update_team_totals(
                team_totals, player_box_score, total_fgm, total_fga, player.team_id, playing_team.id
            )

        # Calculate team percentage stats
        self._calculate_team_percentages(team_totals)

        # Create game summary
        game_summary = self._create_game_summary(game, playing_team, opponent_team, team_totals)

        # Sort players by points (descending) for better display
        player_stats_list.sort(key=lambda x: x["points"], reverse=True)  # type: ignore

        return player_stats_list, game_summary

    def generate_player_performance_report(self, player_id: int, game_id: int) -> dict:
        """
        Generate a comprehensive performance report for a single player in a specific game.

        This detailed report includes all tracked statistics along with analysis of
        the player's performance in the game. It provides a quarter-by-quarter breakdown
        of the player's statistics, allowing coaches and players to identify patterns,
        hot streaks, or areas for improvement throughout the game.

        The report includes:
        - Basic statistics (points, shooting percentages)
        - Advanced metrics (eFG%, TS%, PPSA)
        - Scoring distribution (% of points from FTs, 2pts, 3pts)
        - Quarter-by-quarter breakdown of all shooting statistics
        - Game context (opponent, date)

        Args:
            player_id: ID of the player to generate the report for
            game_id: ID of the game to analyze

        Returns:
            Dictionary with player performance data including quarter-by-quarter breakdown

        Raises:
            ValueError: If the player or game is not found, or if no stats exist for the player in this game
        """
        game, playing_team, opponent_team = self._fetch_game_and_teams(game_id)
        if not game:
            raise ValueError(f"Game not found with id: {game_id}")

        player = crud_player.get_player_by_id(self.db_session, player_id)
        if not player:
            raise ValueError(f"Player not found with id: {player_id}")

        # Get player stats for this game
        pgs = crud_player_game_stats.get_player_game_stats(self.db_session, player_id, game_id)
        if not pgs:
            raise ValueError(f"No stats found for player {player_id} in game {game_id}")

        # Get quarter stats
        quarter_stats = crud_player_quarter_stats.get_player_quarter_stats(self.db_session, pgs.id)
        quarter_stats = self._handle_missing_quarter_data(quarter_stats)

        # Calculate the player's box score
        player_box_score, _, _ = self._calculate_player_box_score(
            player, pgs, quarter_stats, playing_team, opponent_team
        )

        # Add additional details for the performance report
        # Format date for display
        date_str = game.date.strftime("%Y-%m-%d") if hasattr(game.date, "strftime") else str(game.date)

        performance_report = {
            **player_box_score,  # Include all box score stats
            "game_date": date_str,
            "opponent": opponent_team.name if player.team_id == playing_team.id else playing_team.name,
            "quarter_breakdown": self._get_quarter_stats_breakdown(quarter_stats),
        }

        return performance_report

    def _get_quarter_stats_breakdown(self, quarter_stats) -> list:
        """
        Break down stats by quarter for detailed analysis.

        Creates a structured quarter-by-quarter breakdown of player statistics,
        calculating key metrics for each quarter individually. This allows for
        analysis of performance trends, hot/cold streaks, and response to game
        situations throughout the course of a game.

        Args:
            quarter_stats: List of PlayerQuarterStats objects with quarter-specific stats

        Returns:
            List of dictionaries with per-quarter stats including points,
            shooting percentages, and shot attempts for each quarter
        """
        quarter_breakdown = []

        # Handle missing quarter data by filling in zeroes
        quarter_map = self._handle_missing_quarter_data(quarter_stats)

        # Process each quarter in order
        for quarter in range(1, 5):
            qs = quarter_map[quarter]

            # Calculate points for this quarter
            quarter_points = qs.ftm + (qs.fg2m * 2) + (qs.fg3m * 3)

            # Add the quarter's stats to the breakdown
            quarter_breakdown.append(
                {
                    "quarter": qs.quarter,
                    "ftm": qs.ftm,
                    "fta": qs.fta,
                    "ft_pct": self.stats_calculator.calculate_percentage(qs.ftm, qs.fta),
                    "fg2m": qs.fg2m,
                    "fg2a": qs.fg2a,
                    "fg2_pct": self.stats_calculator.calculate_percentage(qs.fg2m, qs.fg2a),
                    "fg3m": qs.fg3m,
                    "fg3a": qs.fg3a,
                    "fg3_pct": self.stats_calculator.calculate_percentage(qs.fg3m, qs.fg3a),
                    "points": quarter_points,
                }
            )

        return quarter_breakdown

    def generate_team_efficiency_report(self, team_id: int, game_id: int) -> dict:
        """
        Generate an efficiency report for a team in a specific game.

        This report focuses on efficiency metrics like TS%, eFG%, and PPSA to provide
        insights into offensive efficiency. It helps coaches and analysts understand
        how effectively a team is converting shot attempts into points.

        The report includes:
        - Team-level efficiency metrics (TS%, eFG%, PPSA)
        - Scoring distribution analysis (proportion of points from FTs, 2pts, 3pts)
        - Per-player efficiency breakdowns
        - Game context (opponent, date)

        The efficiency metrics provide different insights:
        - TS% (True Shooting): Overall shooting efficiency including free throws
        - eFG% (Effective Field Goal): Field goal efficiency giving extra weight to 3-pointers
        - PPSA (Points Per Shot Attempt): Direct measure of points generated per attempt

        Args:
            team_id: ID of the team to generate the report for
            game_id: ID of the game to analyze

        Returns:
            Dictionary with team efficiency data including player breakdowns

        Raises:
            ValueError: If the team or game is not found, or if team didn't participate in the game
        """
        game, playing_team, opponent_team = self._fetch_game_and_teams(game_id)
        if not game:
            raise ValueError(f"Game not found with id: {game_id}")

        # Determine which team we're reporting on
        if team_id == playing_team.id:
            selected_team = playing_team
            other_team = opponent_team
        elif team_id == opponent_team.id:
            selected_team = opponent_team
            other_team = playing_team
        else:
            raise ValueError(f"Team with ID {team_id} is not part of game {game_id}")

        # Get player game stats for all players on the selected team in this game
        team_player_game_stats = []
        all_game_stats = crud_player_game_stats.get_player_game_stats_by_game(self.db_session, game_id)

        for pgs in all_game_stats:
            player = crud_player.get_player_by_id(self.db_session, pgs.player_id)
            if player and player.team_id == team_id:
                team_player_game_stats.append(pgs)

        # Initialize team totals
        team_totals = self._initialize_team_totals()

        # Calculate stats for each player and update team totals
        player_efficiency_stats = []
        for pgs in team_player_game_stats:
            player = crud_player.get_player_by_id(self.db_session, pgs.player_id)
            if not player:
                continue

            quarter_stats = crud_player_quarter_stats.get_player_quarter_stats(self.db_session, pgs.id)
            quarter_stats = self._handle_missing_quarter_data(quarter_stats)

            # Calculate player box score
            player_box_score, total_fgm, total_fga = self._calculate_player_box_score(
                player, pgs, quarter_stats, playing_team, opponent_team
            )

            # Add simplified player stats to the list
            player_efficiency_stats.append(
                {
                    "name": player.name,
                    "jersey": player.jersey_number,
                    "points": player_box_score["points"],
                    "ts_pct": player_box_score["ts_pct"],
                    "efg": player_box_score["efg"],
                    "ppsa": player_box_score["ppsa"],
                }
            )

            # Update team totals
            self._update_team_totals(
                team_totals,
                player_box_score,
                total_fgm,
                total_fga,
                player.team_id,
                team_id,  # Use team_id instead of playing_team.id to work with either team
            )

        # Calculate team percentage stats
        self._calculate_team_percentages(team_totals)

        # Format date for display
        date_str = game.date.strftime("%Y-%m-%d") if hasattr(game.date, "strftime") else str(game.date)

        # Create the efficiency report
        efficiency_report = {
            "game_date": date_str,
            "team_name": selected_team.name,
            "opponent_name": other_team.name,
            "team_points": team_totals["points"],
            "team_ts_pct": team_totals["ts_pct"],
            "team_efg": team_totals["efg"],
            "team_ppsa": team_totals["ppsa"],
            "scoring_distribution": team_totals["scoring_distribution"],
            "player_efficiency": player_efficiency_stats,
        }

        return efficiency_report

    def generate_scoring_analysis_report(self, team_id: int, game_id: int) -> dict:
        """
        Generate a scoring analysis report for a team in a specific game.

        This report focuses on how points were generated, breaking down scoring
        by shot type and player contributions. It provides insights into scoring
        patterns and tendencies that can inform coaching decisions and strategy.

        The report includes:
        - Total points by shot type (FT, 2P, 3P)
        - Scoring distribution by shot type (percentages)
        - Quarter-by-quarter scoring breakdown
        - Per-player scoring analysis including:
          - Total points and contribution to team total
          - Points by shot type
          - Quarter-by-quarter scoring

        This analysis helps identify:
        - Most efficient scoring methods for the team
        - Key scoring contributors
        - Scoring patterns over the course of the game
        - Quarter-by-quarter and player-by-player scoring tendencies

        Args:
            team_id: ID of the team to generate the report for
            game_id: ID of the game to analyze

        Returns:
            Dictionary with scoring analysis data organized by shot type and player

        Raises:
            ValueError: If the team or game is not found, or if team didn't participate in the game
        """
        game, playing_team, opponent_team = self._fetch_game_and_teams(game_id)
        if not game:
            raise ValueError(f"Game not found with id: {game_id}")

        # Determine which team we're reporting on
        if team_id == playing_team.id:
            selected_team = playing_team
            other_team = opponent_team
        elif team_id == opponent_team.id:
            selected_team = opponent_team
            other_team = playing_team
        else:
            raise ValueError(f"Team with ID {team_id} is not part of game {game_id}")

        # Get player game stats for this team
        team_player_game_stats = []
        all_game_stats = crud_player_game_stats.get_player_game_stats_by_game(self.db_session, game_id)

        for pgs in all_game_stats:
            player = crud_player.get_player_by_id(self.db_session, pgs.player_id)
            if player and player.team_id == team_id:
                team_player_game_stats.append(pgs)

        # Initialize team totals and scoring data
        team_totals = self._initialize_team_totals()
        player_scoring_data = []
        quarter_scoring = {1: 0, 2: 0, 3: 0, 4: 0}

        # Calculate stats for each player and update team totals
        for pgs in team_player_game_stats:
            player = crud_player.get_player_by_id(self.db_session, pgs.player_id)
            if not player:
                continue

            quarter_stats = crud_player_quarter_stats.get_player_quarter_stats(self.db_session, pgs.id)
            quarter_stats = self._handle_missing_quarter_data(quarter_stats)

            # Calculate player box score
            player_box_score, total_fgm, total_fga = self._calculate_player_box_score(
                player, pgs, quarter_stats, playing_team, opponent_team
            )

            # Calculate per-quarter points for this player
            quarter_points = {}

            # Handle quarter_stats whether it's a list of objects or a dict with integer keys
            if isinstance(quarter_stats, dict):
                # If quarter_stats is a dictionary, iterate over its items
                for quarter_num, qs in quarter_stats.items():
                    # Get values, handling both object attributes and direct values
                    ftm = getattr(qs, "ftm", qs) if hasattr(qs, "ftm") else 0
                    fg2m = getattr(qs, "fg2m", qs) if hasattr(qs, "fg2m") else 0
                    fg3m = getattr(qs, "fg3m", qs) if hasattr(qs, "fg3m") else 0

                    points = ftm + (fg2m * 2) + (fg3m * 3)
                    quarter_points[quarter_num] = points

                    # Add to team quarter totals
                    quarter_scoring[quarter_num] = quarter_scoring.get(quarter_num, 0) + points
            else:
                # If quarter_stats is a list of objects
                for qs in quarter_stats:
                    ftm = qs.ftm if hasattr(qs, "ftm") else 0
                    fg2m = qs.fg2m if hasattr(qs, "fg2m") else 0
                    fg3m = qs.fg3m if hasattr(qs, "fg3m") else 0

                    points = ftm + (fg2m * 2) + (fg3m * 3)
                    # Get quarter number, checking different possible attribute names
                    if hasattr(qs, "quarter"):
                        quarter_number = qs.quarter
                    elif hasattr(qs, "quarter_number"):
                        quarter_number = qs.quarter_number
                    else:
                        quarter_number = 0

                    quarter_points[quarter_number] = points

                    # Add to team quarter totals
                    quarter_scoring[quarter_number] = quarter_scoring.get(quarter_number, 0) + points

            # Add player scoring data
            ft_points = player_box_score["ftm"]
            fg2_points = player_box_score["fg2m"] * 2
            fg3_points = player_box_score["fg3m"] * 3

            player_scoring_data.append(
                {
                    "name": player.name,
                    "jersey": player.jersey_number,
                    "total_points": player_box_score["points"],
                    "ft_points": ft_points,
                    "fg2_points": fg2_points,
                    "fg3_points": fg3_points,
                    "scoring_distribution": player_box_score["scoring_distribution"],
                    "quarter_points": quarter_points,
                }
            )

            # Update team totals
            self._update_team_totals(team_totals, player_box_score, total_fgm, total_fga, player.team_id, team_id)

        # Calculate team percentage stats
        self._calculate_team_percentages(team_totals)

        # Sort players by total points descending
        player_scoring_data.sort(key=lambda x: x["total_points"], reverse=True)

        # Calculate team points from each shot type
        ft_points_team = team_totals["ftm"]
        fg2_points_team = team_totals["fg2m"] * 2
        fg3_points_team = team_totals["fg3m"] * 3

        # Format date for display
        date_str = game.date.strftime("%Y-%m-%d") if hasattr(game.date, "strftime") else str(game.date)

        # Create the scoring analysis report
        scoring_analysis = {
            "game_date": date_str,
            "team_name": selected_team.name,
            "opponent_name": other_team.name,
            "team_points": team_totals["points"],
            "ft_points": ft_points_team,
            "fg2_points": fg2_points_team,
            "fg3_points": fg3_points_team,
            "scoring_distribution": team_totals["scoring_distribution"],
            "quarter_scoring": quarter_scoring,
            "player_scoring": player_scoring_data,
        }

        return scoring_analysis

    def generate_game_flow_report(self, game_id: int) -> dict:
        """
        Generate a game flow report for a specific game.

        This report tracks performance by quarter for both teams, identifying
        momentum shifts and scoring patterns throughout the game. It provides
        insights into how the game dynamics evolved over time, when scoring
        runs occurred, and which quarters were most pivotal.

        The report includes:
        - Quarter-by-quarter scoring for both teams
        - Cumulative scores by quarter
        - Point differentials by quarter
        - Significant scoring runs and momentum shifts

        This analysis helps coaches and players:
        - Identify critical moments where game momentum shifted
        - Understand team performance patterns throughout the game
        - Recognize quarters where adjustments were effective or needed
        - Better prepare for specific game situations in future contests

        Args:
            game_id: ID of the game to analyze

        Returns:
            Dictionary with game flow data including quarter analysis

        Raises:
            ValueError: If the game is not found
        """
        game, playing_team, opponent_team = self._fetch_game_and_teams(game_id)
        if not game:
            raise ValueError(f"Game not found with id: {game_id}")

        # Get all player game stats for this game
        player_game_stats = crud_player_game_stats.get_player_game_stats_by_game(self.db_session, game_id)

        # Initialize quarter scoring for both teams
        playing_team_quarters = {1: 0, 2: 0, 3: 0, 4: 0}
        opponent_team_quarters = {1: 0, 2: 0, 3: 0, 4: 0}

        # Process each player's stats
        for pgs in player_game_stats:
            player = crud_player.get_player_by_id(self.db_session, pgs.player_id)
            if not player:
                continue

            quarter_stats = crud_player_quarter_stats.get_player_quarter_stats(self.db_session, pgs.id)

            # Calculate points for each quarter for this player
            for qs in quarter_stats:
                points = (qs.ftm) + (qs.fg2m * 2) + (qs.fg3m * 3)

                # Add to the appropriate team's quarter totals
                if player.team_id == playing_team.id:
                    playing_team_quarters[qs.quarter_number] += points
                elif player.team_id == opponent_team.id:
                    opponent_team_quarters[qs.quarter_number] += points

        # Calculate cumulative scores
        playing_team_cumulative = {
            1: playing_team_quarters[1],
            2: playing_team_quarters[1] + playing_team_quarters[2],
            3: playing_team_quarters[1] + playing_team_quarters[2] + playing_team_quarters[3],
            4: playing_team_quarters[1]
            + playing_team_quarters[2]
            + playing_team_quarters[3]
            + playing_team_quarters[4],
        }

        opponent_team_cumulative = {
            1: opponent_team_quarters[1],
            2: opponent_team_quarters[1] + opponent_team_quarters[2],
            3: opponent_team_quarters[1] + opponent_team_quarters[2] + opponent_team_quarters[3],
            4: (
                opponent_team_quarters[1]
                + opponent_team_quarters[2]
                + opponent_team_quarters[3]
                + opponent_team_quarters[4]
            ),
        }

        # Identify scoring runs
        scoring_runs = self._identify_scoring_runs(playing_team_quarters, opponent_team_quarters)

        # Calculate point differentials by quarter
        point_differentials = {
            quarter: playing_team_quarters[quarter] - opponent_team_quarters[quarter] for quarter in range(1, 5)
        }

        # Format date for display
        date_str = game.date.strftime("%Y-%m-%d") if hasattr(game.date, "strftime") else str(game.date)

        # Create the game flow report
        game_flow_report = {
            "game_date": date_str,
            "playing_team": {
                "name": playing_team.name,
                "quarter_scoring": playing_team_quarters,
                "cumulative_score": playing_team_cumulative,
                "total_points": sum(playing_team_quarters.values()),
            },
            "opponent_team": {
                "name": opponent_team.name,
                "quarter_scoring": opponent_team_quarters,
                "cumulative_score": opponent_team_cumulative,
                "total_points": sum(opponent_team_quarters.values()),
            },
            "point_differentials": point_differentials,
            "scoring_runs": scoring_runs,
        }

        return game_flow_report

    def _identify_scoring_runs(self, team_a_quarters: dict, team_b_quarters: dict) -> list:
        """
        Identify significant scoring runs or droughts by comparing quarter-by-quarter performance.

        Analyzes each quarter to find periods where one team significantly outscored
        the other, which typically indicate momentum shifts, hot/cold streaks, or
        tactical advantages. These scoring runs are often the key moments that decide
        game outcomes.

        Args:
            team_a_quarters: Dictionary of team A's scoring by quarter (playing team)
            team_b_quarters: Dictionary of team B's scoring by quarter (opponent team)

        Returns:
            List of dictionaries describing significant scoring runs, including which team
            had the advantage, the quarter it occurred in, and the point differential
        """
        runs = []

        # Look for quarters where one team outscores the other by a significant margin
        for quarter in range(1, 5):
            differential = team_a_quarters[quarter] - team_b_quarters[quarter]

            # Define a "significant" run as outscoring by 5+ points
            if differential >= 5:
                runs.append(
                    {
                        "quarter": quarter,
                        "team": "playing",
                        "differential": differential,
                        "description": f"Playing team outscored opponent by {differential} in Q{quarter}",
                    }
                )
            elif differential <= -5:
                runs.append(
                    {
                        "quarter": quarter,
                        "team": "opponent",
                        "differential": -differential,
                        "description": f"Opponent team outscored playing team by {-differential} in Q{quarter}",
                    }
                )

        return runs
