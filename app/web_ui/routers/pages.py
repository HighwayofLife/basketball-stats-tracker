"""HTML pages router for Basketball Stats Tracker."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import desc
from sqlalchemy.orm import joinedload

from app.data_access import models
from app.data_access.db_session import get_db_session
from app.services.score_calculation_service import ScoreCalculationService
from app.web_ui.dependencies import get_template_auth_context
from app.web_ui.templates_config import templates

logger = logging.getLogger(__name__)
router = APIRouter(tags=["pages"])


def get_top_players_from_recent_week(session, limit=4):
    """Get top players from the most recent week when games were played."""
    # Find the most recent game date
    most_recent_game = session.query(models.Game).order_by(desc(models.Game.date)).first()

    if not most_recent_game:
        return []

    # Get all games from the most recent date (or week if we want to extend)
    recent_date = most_recent_game.date

    # Get all player stats from games on that date
    player_stats = (
        session.query(models.PlayerGameStats, models.Player, models.Team, models.Game)
        .join(models.Player, models.PlayerGameStats.player_id == models.Player.id)
        .join(models.Team, models.Player.team_id == models.Team.id)
        .join(models.Game, models.PlayerGameStats.game_id == models.Game.id)
        .filter(models.Game.date == recent_date)
        .all()
    )

    # Calculate points and create player data
    top_players_data = []
    for stat, player, team, game in player_stats:
        points = ScoreCalculationService.calculate_player_points(stat)

        # Calculate field goal percentages
        fg_made = stat.total_2pm + stat.total_3pm
        fg_attempted = stat.total_2pa + stat.total_3pa
        fg_percentage = (fg_made / fg_attempted * 100) if fg_attempted > 0 else 0

        fg3_percentage = (stat.total_3pm / stat.total_3pa * 100) if stat.total_3pa > 0 else 0

        # Determine opponent team
        opponent_team = game.opponent_team if player.team_id == game.playing_team_id else game.playing_team
        opponent_name = opponent_team.display_name or opponent_team.name if opponent_team else "Unknown"

        top_players_data.append(
            {
                "name": player.name,
                "team_name": team.display_name or team.name,
                "points": points,
                "fg_made": fg_made,
                "fg_attempted": fg_attempted,
                "fg_percentage": fg_percentage,
                "fg3_made": stat.total_3pm,
                "fg3_attempted": stat.total_3pa,
                "fg3_percentage": fg3_percentage,
                "total_2pm": stat.total_2pm,
                "total_2pa": stat.total_2pa,
                "total_3pm": stat.total_3pm,
                "total_3pa": stat.total_3pa,
                "total_ftm": stat.total_ftm,
                "total_fta": stat.total_fta,
                "game_date": game.date,
                "opponent": opponent_name,
                "game_id": game.id,
            }
        )

    # Sort by points descending and return top players
    top_players_data.sort(key=lambda x: x["points"], reverse=True)
    return top_players_data[:limit]


@router.get("/", response_class=HTMLResponse)
async def index(auth_context: dict = Depends(get_template_auth_context)):
    """Render the dashboard home page."""
    try:
        with get_db_session() as session:
            # Get recent games for dashboard
            recent_games = (
                session.query(models.Game)
                .options(
                    # Eagerly load relationships to avoid lazy loading issues
                    joinedload(models.Game.playing_team),
                    joinedload(models.Game.opponent_team),
                )
                .order_by(models.Game.date.desc())
                .limit(5)
                .all()
            )

            # Convert to dictionary for template, calculating scores from player stats
            recent_games_data = []
            for game in recent_games:
                try:
                    # Get player stats for both teams
                    playing_team_stats = (
                        session.query(models.PlayerGameStats)
                        .join(models.Player)
                        .filter(
                            models.PlayerGameStats.game_id == game.id,
                            models.Player.team_id == game.playing_team_id,
                        )
                        .all()
                    )

                    opponent_team_stats = (
                        session.query(models.PlayerGameStats)
                        .join(models.Player)
                        .filter(
                            models.PlayerGameStats.game_id == game.id,
                            models.Player.team_id == game.opponent_team_id,
                        )
                        .all()
                    )

                    # Calculate team scores from player stats
                    home_score = sum(ScoreCalculationService.calculate_player_points(s) for s in playing_team_stats)
                    away_score = sum(ScoreCalculationService.calculate_player_points(s) for s in opponent_team_stats)

                    recent_games_data.append(
                        {
                            "id": game.id,
                            "date": game.date,
                            "home_team": (
                                game.playing_team.display_name or game.playing_team.name
                                if game.playing_team
                                else "Unknown"
                            ),
                            "away_team": (
                                game.opponent_team.display_name or game.opponent_team.name
                                if game.opponent_team
                                else "Unknown"
                            ),
                            "home_score": home_score,
                            "away_score": away_score,
                        }
                    )
                except Exception as game_error:
                    logger.warning(f"Error processing game {game.id}: {game_error}")
                    # Skip this game if there's an error processing it
                    continue

            # Get top players from recent games
            top_players = get_top_players_from_recent_week(session, limit=4)

            context = {
                **auth_context,
                "title": "Basketball Stats Dashboard",
                "recent_games": recent_games_data,
                "top_players": top_players,
            }

            return templates.TemplateResponse("index.html", context)
    except Exception as e:
        logger.error(f"Error rendering dashboard: {e}")
        # Return an empty dashboard instead of error
        context = {
            **auth_context,
            "title": "Basketball Stats Dashboard",
            "recent_games": [],
            "top_players": [],
        }
        return templates.TemplateResponse("index.html", context)


@router.get("/games", response_class=HTMLResponse)
async def games_page(auth_context: dict = Depends(get_template_auth_context)):
    """Render the games list page."""
    context = {**auth_context, "title": "Basketball Games"}
    return templates.TemplateResponse("games/index.html", context)


@router.get("/games/create", response_class=HTMLResponse)
async def create_game_page(auth_context: dict = Depends(get_template_auth_context)):
    """Render the create game page."""
    context = {**auth_context, "title": "Create New Game"}
    return templates.TemplateResponse("games/create.html", context)


@router.get("/teams", response_class=HTMLResponse)
async def teams_page(auth_context: dict = Depends(get_template_auth_context)):
    """Render the teams management page."""
    context = {**auth_context, "title": "Team Management"}
    return templates.TemplateResponse("teams/index.html", context)


@router.get("/teams/{team_id}", response_class=HTMLResponse)
async def team_detail_page(team_id: int, auth_context: dict = Depends(get_template_auth_context)):
    """Render the team detail page."""
    context = {**auth_context, "title": "Team Details", "team_id": team_id}
    return templates.TemplateResponse("teams/detail.html", context)


@router.get("/players", response_class=HTMLResponse)
async def players_page(auth_context: dict = Depends(get_template_auth_context)):
    """Render the players management page."""
    context = {**auth_context, "title": "Player Management"}
    return templates.TemplateResponse("players/index.html", context)


@router.get("/games/{game_id}", response_class=HTMLResponse)
async def game_detail_page(game_id: int, auth_context: dict = Depends(get_template_auth_context)):
    """Render the game detail page with box score."""
    try:
        with get_db_session() as session:
            game = session.query(models.Game).filter(models.Game.id == game_id).first()

            if not game:
                raise HTTPException(status_code=404, detail="Game not found")

            context = {
                **auth_context,
                "title": (
                    f"{game.opponent_team.display_name or game.opponent_team.name} @ "
                    f"{game.playing_team.display_name or game.playing_team.name}"
                ),
                "game_id": game_id,
            }
            return templates.TemplateResponse("games/detail.html", context)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering game detail page: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/games/{game_id}/edit-stats", response_class=HTMLResponse)
async def game_edit_stats_page(game_id: int, auth_context: dict = Depends(get_template_auth_context)):
    """Render the game stats editing page."""
    try:
        with get_db_session() as session:
            game = session.query(models.Game).filter(models.Game.id == game_id).first()

            if not game:
                raise HTTPException(status_code=404, detail="Game not found")

            # Get player stats for both teams
            playing_team_stats = (
                session.query(models.PlayerGameStats)
                .join(models.Player)
                .filter(
                    models.PlayerGameStats.game_id == game_id,
                    models.Player.team_id == game.playing_team_id,
                )
                .order_by(models.Player.jersey_number)
                .all()
            )

            opponent_team_stats = (
                session.query(models.PlayerGameStats)
                .join(models.Player)
                .filter(
                    models.PlayerGameStats.game_id == game_id,
                    models.Player.team_id == game.opponent_team_id,
                )
                .order_by(models.Player.jersey_number)
                .all()
            )

            # Calculate team scores
            home_score = sum(s.total_ftm + s.total_2pm * 2 + s.total_3pm * 3 for s in playing_team_stats)
            away_score = sum(s.total_ftm + s.total_2pm * 2 + s.total_3pm * 3 for s in opponent_team_stats)

            context = {
                **auth_context,
                "title": f"Edit Stats - {game.opponent_team.name} @ {game.playing_team.name}",
                "game": game,
                "playing_team_stats": playing_team_stats,
                "opponent_team_stats": opponent_team_stats,
                "home_score": home_score,
                "away_score": away_score,
            }
            return templates.TemplateResponse("games/edit_stats.html", context)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering game edit stats page: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/games/{game_id}/live", response_class=HTMLResponse)
async def game_live_entry_page(game_id: int, auth_context: dict = Depends(get_template_auth_context)):
    """Render the live game entry page."""
    try:
        with get_db_session() as session:
            game = session.query(models.Game).filter(models.Game.id == game_id).first()

            if not game:
                raise HTTPException(status_code=404, detail="Game not found")

            context = {
                **auth_context,
                "title": f"Live Entry: {game.opponent_team.name} @ {game.playing_team.name}",
                "game_id": game_id,
                "home_team": game.playing_team.name,
                "away_team": game.opponent_team.name,
            }
            return templates.TemplateResponse("games/live_entry.html", context)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering live entry page: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/admin/data-corrections", response_class=HTMLResponse)
async def admin_data_corrections_page(auth_context: dict = Depends(get_template_auth_context)):
    """Render the data corrections admin page."""
    context = {**auth_context, "title": "Data Corrections Admin"}
    return templates.TemplateResponse("admin/data_corrections.html", context)


@router.get("/players/{player_id}", response_class=HTMLResponse)
async def player_detail_page(player_id: int, auth_context: dict = Depends(get_template_auth_context)):
    """Render the player detail page."""
    try:
        with get_db_session() as session:
            player = session.query(models.Player).filter(models.Player.id == player_id).first()

            if not player:
                raise HTTPException(status_code=404, detail="Player not found")

            context = {
                **auth_context,
                "title": f"{player.name} - Player Profile",
                "player_id": player_id,
            }
            return templates.TemplateResponse("players/detail.html", context)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering player detail page: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/scorebook", response_class=HTMLResponse)
async def scorebook_entry_page(auth_context: dict = Depends(get_template_auth_context)):
    """Render the scorebook entry page."""
    context = {**auth_context, "title": "Scorebook Entry"}
    return templates.TemplateResponse("games/scorebook_entry.html", context)


@router.get("/login", response_class=HTMLResponse)
async def login_page(auth_context: dict = Depends(get_template_auth_context)):
    """Render the login page."""
    context = {**auth_context, "title": "Login"}
    return templates.TemplateResponse("auth/login.html", context)


@router.get("/account", response_class=HTMLResponse)
async def account_page(auth_context: dict = Depends(get_template_auth_context)):
    """Render the account management page."""
    context = {**auth_context, "title": "Account Settings"}
    return templates.TemplateResponse("auth/account.html", context)


@router.get("/admin/users", response_class=HTMLResponse)
async def admin_users_page(auth_context: dict = Depends(get_template_auth_context)):
    """Render the user management page (admin only)."""
    context = {**auth_context, "title": "User Management"}
    return templates.TemplateResponse("admin/users.html", context)


@router.get("/admin/seasons", response_class=HTMLResponse)
async def admin_seasons_page(auth_context: dict = Depends(get_template_auth_context)):
    """Render the seasons management page (admin only)."""
    context = {**auth_context, "title": "Season Management"}
    return templates.TemplateResponse("admin/seasons.html", context)


@router.get("/logout")
async def logout_page(request: Request, auth_context: dict = Depends(get_template_auth_context)):
    """Handle logout by clearing cookies and localStorage, then redirecting."""
    # Return a logout page that clears localStorage before redirecting

    # Create HTML response that clears localStorage and redirects
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Logging out...</title>
        <meta http-equiv="refresh" content="2;url=/">
    </head>
    <body>
        <p>Logging out...</p>
        <script>
            // Clear localStorage tokens
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            localStorage.removeItem('token_type');
            // Redirect to home page after clearing tokens
            setTimeout(function() {
                window.location.href = '/';
            }, 100);
        </script>
    </body>
    </html>
    """

    response = HTMLResponse(content=html_content)
    # Clear authentication cookies
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")
    return response


@router.get("/about", response_class=HTMLResponse)
async def about_page(auth_context: dict = Depends(get_template_auth_context)):
    """Render the about page."""
    context = {**auth_context, "title": "About"}
    return templates.TemplateResponse("about.html", context)
