from sqlalchemy.orm import Session

from app.data_access.crud import crud_game, crud_player_game_stats, crud_player_quarter_stats, crud_player, crud_team


class ReportGenerator:
    def __init__(self, db_session: Session, stats_calculator_module):
        self.db_session = db_session
        self.stats_calculator = stats_calculator_module

    def get_game_box_score_data(self, game_id: int) -> tuple[list[dict], dict]:
        """
        Generate a box score report for a game.
        
        Args:
            game_id: ID of the game to generate report for.
            
        Returns:
            A tuple containing:
            - List of player stats dictionaries (box score data)
            - Game summary dictionary (team totals, game information)
        """
        # Fetch the game data
        game = crud_game.get_game_by_id(self.db_session, game_id)
        if not game:
            return [], {}
        
        # Fetch the teams
        playing_team = crud_team.get_team_by_id(self.db_session, game.playing_team_id)
        opponent_team = crud_team.get_team_by_id(self.db_session, game.opponent_team_id)
        
        if not playing_team or not opponent_team:
            return [], {}
        
        # Fetch all player game stats for this game
        player_game_stats = crud_player_game_stats.get_player_game_stats_by_game(
            self.db_session, game_id
        )
        
        player_stats_list = []
        team_totals = {
            "points": 0,
            "ftm": 0, "fta": 0,
            "fg2m": 0, "fg2a": 0,
            "fg3m": 0, "fg3a": 0,
            "fouls": 0,
            "total_fgm": 0, "total_fga": 0
        }
        
        for pgs in player_game_stats:
            # Get the player
            player = crud_player.get_player_by_id(self.db_session, pgs.player_id)
            if not player:
                continue
                
            # Get all quarter stats for this player in this game
            quarter_stats = crud_player_quarter_stats.get_player_quarter_stats(
                self.db_session, pgs.id
            )
            
            # Determine the team name
            team_name = ""
            if player.team_id == playing_team.id:
                team_name = playing_team.name
            elif player.team_id == opponent_team.id:
                team_name = opponent_team.name
            else:
                team_name = "Unknown Team"
                
            # Initialize stats for this player
            player_box_score = {
                "player_name": player.name,
                "player_jersey": player.jersey_number,
                "team_name": team_name,
                "fouls": pgs.fouls,
                "ftm": 0, "fta": 0, "ft_pct": None,
                "fg2m": 0, "fg2a": 0, "fg2_pct": None,
                "fg3m": 0, "fg3a": 0, "fg3_pct": None,
                "points": 0,
                "efg": None,
                "ts_pct": None
            }
            
            # Aggregate stats from all quarters
            for qs in quarter_stats:
                player_box_score["ftm"] += qs.ftm if qs.ftm is not None else 0
                player_box_score["fta"] += qs.fta if qs.fta is not None else 0
                player_box_score["fg2m"] += qs.fg2m if qs.fg2m is not None else 0
                player_box_score["fg2a"] += qs.fg2a if qs.fg2a is not None else 0
                player_box_score["fg3m"] += qs.fg3m if qs.fg3m is not None else 0
                player_box_score["fg3a"] += qs.fg3a if qs.fg3a is not None else 0
            
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
            total_fgm = player_box_score["fg2m"] + player_box_score["fg3m"]
            total_fga = player_box_score["fg2a"] + player_box_score["fg3a"]
            
            player_box_score["efg"] = self.stats_calculator.calculate_efg(
                total_fgm, player_box_score["fg3m"], total_fga
            )
            
            player_box_score["ts_pct"] = self.stats_calculator.calculate_ts(
                player_box_score["points"], total_fga, player_box_score["fta"]
            )
            
            # Add player to report list
            player_stats_list.append(player_box_score)
            
            # Update team totals if this player is on the playing team
            if player.team_id == playing_team.id:
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
                
        # Calculate team percentage stats
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
        
        # Create game summary with team data and game information
        game_summary = {
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
            "team_ts_pct": team_totals["ts_pct"]
        }
        
        # Sort players by points (descending) for better display
        player_stats_list.sort(key=lambda x: x["points"], reverse=True)
        
        return player_stats_list, game_summary
