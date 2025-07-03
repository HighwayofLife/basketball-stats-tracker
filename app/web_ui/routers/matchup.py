"""Matchup preview router for scheduled games."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.data_access.db_session import get_db_session
from app.services.matchup_service import MatchupService
from app.web_ui.dependencies import get_template_auth_context
from app.web_ui.templates_config import templates

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scheduled-games", tags=["matchup"])


@router.get("/{scheduled_game_id}/matchup", response_class=HTMLResponse)
async def view_matchup(
    request: Request,
    scheduled_game_id: int,
    auth_context: dict = Depends(get_template_auth_context),
):
    """
    Display matchup preview for a scheduled game.

    Args:
        request: FastAPI request object
        scheduled_game_id: The ID of the scheduled game

    Returns:
        HTML response with the matchup preview page
    """
    try:
        with get_db_session() as session:
            matchup_service = MatchupService(session)
            matchup_data = matchup_service.get_matchup_data(scheduled_game_id)

            if not matchup_data:
                raise HTTPException(status_code=404, detail="Scheduled game not found")

            # Format the data for the template
            context = {
                **auth_context,  # Include authentication context
                "scheduled_game": matchup_data["scheduled_game"],
                "home_team": matchup_data["home_team"],
                "away_team": matchup_data["away_team"],
                "head_to_head": matchup_data["head_to_head"],
            }

            # Add computed statistics for display
            # Home team stats
            home_stats = matchup_data["home_team"]["season_stats"]
            if home_stats:
                context["home_team"]["ppg"] = round(home_stats["ppg"], 1)
                context["home_team"]["opp_ppg"] = round(home_stats["opp_ppg"], 1)
                context["home_team"]["record"] = matchup_service._format_team_record(
                    home_stats["wins"], home_stats["losses"]
                )
                context["home_team"]["win_pct"] = round(home_stats["win_percentage"] * 100, 1)
                context["home_team"]["ft_pct"] = round(home_stats["ft_percentage"] * 100, 1)
                context["home_team"]["fg2_pct"] = round(home_stats["fg2_percentage"] * 100, 1)
                context["home_team"]["fg3_pct"] = round(home_stats["fg3_percentage"] * 100, 1)
            else:
                context["home_team"]["ppg"] = 0
                context["home_team"]["opp_ppg"] = 0
                context["home_team"]["record"] = matchup_service._format_team_record(0, 0)
                context["home_team"]["win_pct"] = 0
                context["home_team"]["ft_pct"] = 0
                context["home_team"]["fg2_pct"] = 0
                context["home_team"]["fg3_pct"] = 0

            # Away team stats
            away_stats = matchup_data["away_team"]["season_stats"]
            if away_stats:
                context["away_team"]["ppg"] = round(away_stats["ppg"], 1)
                context["away_team"]["opp_ppg"] = round(away_stats["opp_ppg"], 1)
                context["away_team"]["record"] = matchup_service._format_team_record(
                    away_stats["wins"], away_stats["losses"]
                )
                context["away_team"]["win_pct"] = round(away_stats["win_percentage"] * 100, 1)
                context["away_team"]["ft_pct"] = round(away_stats["ft_percentage"] * 100, 1)
                context["away_team"]["fg2_pct"] = round(away_stats["fg2_percentage"] * 100, 1)
                context["away_team"]["fg3_pct"] = round(away_stats["fg3_percentage"] * 100, 1)
            else:
                context["away_team"]["ppg"] = 0
                context["away_team"]["opp_ppg"] = 0
                context["away_team"]["record"] = matchup_service._format_team_record(0, 0)
                context["away_team"]["win_pct"] = 0
                context["away_team"]["ft_pct"] = 0
                context["away_team"]["fg2_pct"] = 0
                context["away_team"]["fg3_pct"] = 0

            # Format top players for display
            for team_key in ["home_team", "away_team"]:
                formatted_players = []
                for player_data in context[team_key]["top_players"]:
                    stats = player_data["raw_stats"]
                    player = player_data["player"]

                    # Calculate percentages
                    ft_pct = round((stats.total_ftm / stats.total_fta * 100) if stats.total_fta > 0 else 0, 1)
                    fg3_pct = round((stats.total_3pm / stats.total_3pa * 100) if stats.total_3pa > 0 else 0, 1)

                    # Calculate overall field goal percentage (2P + 3P combined)
                    total_fg_made = stats.total_2pm + stats.total_3pm
                    total_fg_attempted = stats.total_2pa + stats.total_3pa
                    fg_pct = round((total_fg_made / total_fg_attempted * 100) if total_fg_attempted > 0 else 0, 1)
                    formatted_players.append(
                        {
                            "id": player.id,
                            "name": player.name,
                            "jersey_number": player.jersey_number,
                            "position": player.position or "N/A",
                            "ppg": round(player_data["ppg"], 1),
                            "games_played": stats.games_played,
                            "ft_pct": ft_pct,
                            "fg_pct": fg_pct,
                            "fg3_pct": fg3_pct,
                        }
                    )
                context[team_key]["top_players"] = formatted_players

            # Format head-to-head history
            formatted_h2h = []
            for game in context["head_to_head"]:
                # Determine winner and format score
                if game.playing_team_score > game.opponent_team_score:
                    winner = game.playing_team.display_name or game.playing_team.name
                    score_display = (
                        f"{game.playing_team.display_name or game.playing_team.name} {game.playing_team_score}, "
                        f"{game.opponent_team.display_name or game.opponent_team.name} {game.opponent_team_score}"
                    )
                else:
                    winner = game.opponent_team.display_name or game.opponent_team.name
                    score_display = (
                        f"{game.opponent_team.display_name or game.opponent_team.name} {game.opponent_team_score}, "
                        f"{game.playing_team.display_name or game.playing_team.name} {game.playing_team_score}"
                    )

                formatted_h2h.append(
                    {
                        "date": game.date.strftime("%m/%d/%Y") if game.date else "N/A",
                        "score": score_display,
                        "winner": winner,
                    }
                )
            context["head_to_head"] = formatted_h2h

            return templates.TemplateResponse("matchup.html", context)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error viewing matchup for scheduled game {scheduled_game_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to load matchup preview") from e
