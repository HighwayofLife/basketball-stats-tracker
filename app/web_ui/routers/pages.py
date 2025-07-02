"""HTML pages router for Basketball Stats Tracker."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from sqlalchemy import desc
from sqlalchemy.orm import joinedload

from app.data_access import models
from app.data_access.db_session import get_db_session
from app.services.score_calculation_service import ScoreCalculationService
from app.services.season_stats_service import SeasonStatsService
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

            # Get all team IDs from recent games for efficient record lookup
            team_ids = set()
            for game in recent_games:
                if game.playing_team_id:
                    team_ids.add(game.playing_team_id)
                if game.opponent_team_id:
                    team_ids.add(game.opponent_team_id)

            # Get team records
            stats_service = SeasonStatsService(session)
            team_records = stats_service.get_teams_records(list(team_ids)) if team_ids else {}

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

                    # Get team records
                    home_wins, home_losses = team_records.get(game.playing_team_id, (0, 0))
                    away_wins, away_losses = team_records.get(game.opponent_team_id, (0, 0))

                    recent_games_data.append(
                        {
                            "id": game.id,
                            "date": game.date,
                            "home_team": (
                                game.playing_team.display_name or game.playing_team.name
                                if game.playing_team
                                else "Unknown"
                            ),
                            "home_team_id": game.playing_team_id,
                            "home_team_record": f"{home_wins}-{home_losses}",
                            "away_team": (
                                game.opponent_team.display_name or game.opponent_team.name
                                if game.opponent_team
                                else "Unknown"
                            ),
                            "away_team_id": game.opponent_team_id,
                            "away_team_record": f"{away_wins}-{away_losses}",
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
    try:
        with get_db_session() as session:
            # Get games with team records (reuse the existing logic)
            from app.services.score_calculation_service import ScoreCalculationService

            # Get completed games
            completed_games = session.query(models.Game).order_by(desc(models.Game.date)).limit(20).all()

            # Get scheduled games
            scheduled_games = (
                session.query(models.ScheduledGame)
                .filter(
                    models.ScheduledGame.status == models.ScheduledGameStatus.SCHEDULED,
                    models.ScheduledGame.is_deleted.is_not(True),
                )
                .order_by(desc(models.ScheduledGame.scheduled_date))
                .limit(10)
                .all()
            )

            # Get all team IDs for efficient record lookup
            team_ids = set()
            for game in completed_games:
                if game.playing_team_id:
                    team_ids.add(game.playing_team_id)
                if game.opponent_team_id:
                    team_ids.add(game.opponent_team_id)
            for scheduled_game in scheduled_games:
                if scheduled_game.home_team_id:
                    team_ids.add(scheduled_game.home_team_id)
                if scheduled_game.away_team_id:
                    team_ids.add(scheduled_game.away_team_id)

            # Get team records
            stats_service = SeasonStatsService(session)
            team_records = stats_service.get_teams_records(list(team_ids)) if team_ids else {}

            # Convert to games data
            games_data = []

            # Add completed games
            for game in completed_games:
                # Get player stats for scoring
                player_stats = (
                    session.query(models.PlayerGameStats).filter(models.PlayerGameStats.game_id == game.id).all()
                )

                # Calculate scores
                playing_team_score, opponent_team_score = ScoreCalculationService.calculate_game_scores(
                    game, player_stats
                )

                # Get team records
                home_wins, home_losses = team_records.get(game.playing_team_id, (0, 0))
                away_wins, away_losses = team_records.get(game.opponent_team_id, (0, 0))

                games_data.append(
                    {
                        "id": game.id,
                        "date": game.date,
                        "home_team": game.playing_team.display_name or game.playing_team.name,
                        "home_team_id": game.playing_team_id,
                        "home_team_record": f"{home_wins}-{home_losses}",
                        "away_team": game.opponent_team.display_name or game.opponent_team.name,
                        "away_team_id": game.opponent_team_id,
                        "away_team_record": f"{away_wins}-{away_losses}",
                        "home_score": playing_team_score,
                        "away_score": opponent_team_score,
                    }
                )

            # Add scheduled games
            for scheduled_game in scheduled_games:
                home_wins, home_losses = team_records.get(scheduled_game.home_team_id, (0, 0))
                away_wins, away_losses = team_records.get(scheduled_game.away_team_id, (0, 0))

                games_data.append(
                    {
                        "id": -scheduled_game.id,  # Negative for scheduled games
                        "date": scheduled_game.scheduled_date,
                        "home_team": scheduled_game.home_team.display_name or scheduled_game.home_team.name,
                        "home_team_id": scheduled_game.home_team_id,
                        "home_team_record": f"{home_wins}-{home_losses}",
                        "away_team": scheduled_game.away_team.display_name or scheduled_game.away_team.name,
                        "away_team_id": scheduled_game.away_team_id,
                        "away_team_record": f"{away_wins}-{away_losses}",
                        "home_score": 0,
                        "away_score": 0,
                    }
                )

            # Sort by date (newest first)
            games_data.sort(key=lambda x: x["date"], reverse=True)

            context = {
                **auth_context,
                "title": "Basketball Games",
                "games": games_data,
                "show_edit_actions": auth_context.get("is_authenticated", False),
            }
            return templates.TemplateResponse("games/index.html", context)

    except Exception as e:
        logger.error(f"Error rendering games page: {e}")
        context = {**auth_context, "title": "Basketball Games", "games": [], "show_edit_actions": False}
        return templates.TemplateResponse("games/index.html", context)


@router.get("/games/create", response_class=HTMLResponse)
async def create_game_page(auth_context: dict = Depends(get_template_auth_context)):
    """Render the create game page."""
    context = {**auth_context, "title": "Create New Game"}
    return templates.TemplateResponse("games/create.html", context)


@router.get("/teams", response_class=HTMLResponse)
async def teams_page(request: Request, auth_context: dict = Depends(get_template_auth_context)):
    """Render the teams management page."""
    # Check for tab parameter in URL
    raw_tab = request.query_params.get("tab", "teams")
    # Only allow valid tab values, default to 'teams' for any invalid value
    active_tab = raw_tab if raw_tab in ["teams", "rankings"] else "teams"

    context = {**auth_context, "title": "Team Management", "active_tab": active_tab}
    return templates.TemplateResponse("teams/index.html", context)


@router.get("/teams/{team_id}", response_class=HTMLResponse)
async def team_detail_page(team_id: int, auth_context: dict = Depends(get_template_auth_context)):
    """Render the team detail page."""
    try:
        with get_db_session() as session:
            team = session.query(models.Team).filter(models.Team.id == team_id).first()

            # For page routes, we load the page even if team doesn't exist
            # The JavaScript will handle showing the error to the user
            context = {**auth_context, "title": "Team Details", "team_id": team_id, "team": team}
            return templates.TemplateResponse("teams/detail.html", context)
    except Exception as e:
        logger.error(f"Error loading team detail page: {e}")
        raise HTTPException(status_code=500, detail="Failed to load team") from e


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
async def logout_page(request: Request):
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


@router.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt():
    """Serve robots.txt file."""
    content = """User-agent: *
Allow: /"""
    return PlainTextResponse(content=content, media_type="text/plain")


@router.get("/.well-known/security.txt", response_class=PlainTextResponse)
async def security_txt():
    """Serve security.txt file."""
    content = """Contact: https://github.com/HighwayofLife/basketball-stats-tracker/issues
Expires: 2025-12-31T23:59:59.000Z
Preferred-Languages: en
Canonical: https://league-stats.net/.well-known/security.txt"""
    return PlainTextResponse(content=content, media_type="text/plain")
