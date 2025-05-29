"""Reports router for web UI."""

import csv
import io
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.data_access.crud import (
    crud_game,
    crud_player,
    crud_player_game_stats,
    crud_player_season_stats,
    crud_team,
    crud_team_season_stats,
)
from app.reports.report_generator import ReportGenerator
from app.services.season_stats_service import SeasonStatsService
from app.utils import stats_calculator
from app.web_ui.dependencies import get_db
from app.web_ui.templates_config import templates

router = APIRouter()


@router.get("/reports", response_class=HTMLResponse)
async def reports_index(request: Request):
    """Display reports index page."""
    return templates.TemplateResponse("reports/index.html", {"request": request})


@router.get("/reports/player-season-select", response_class=HTMLResponse)
async def player_season_select(request: Request):
    """Display player selection page for season reports."""
    return templates.TemplateResponse("reports/player_season_select.html", {"request": request})


@router.get("/reports/team-season-select", response_class=HTMLResponse)
async def team_season_select(request: Request):
    """Display team selection page for season reports."""
    return templates.TemplateResponse("reports/team_season_select.html", {"request": request})


@router.get("/v1/reports/games", response_model=dict[str, Any])
async def get_games_for_reports(
    db: Annotated[Session, Depends(get_db)],
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
    team_id: Annotated[int | None, Query()] = None,
):
    """Get list of games for report selection."""
    games = crud_game.get_all_games(db)

    # Filter by date range if provided
    if start_date:
        games = [g for g in games if g.date >= start_date]
    if end_date:
        games = [g for g in games if g.date <= end_date]

    # Filter by team if provided
    if team_id:
        games = [g for g in games if g.playing_team_id == team_id or g.opponent_team_id == team_id]

    # Calculate scores for each game
    game_list = []
    for game in sorted(games, key=lambda g: g.date, reverse=True):
        # Calculate team scores from player stats
        playing_team_score = 0
        opponent_team_score = 0

        for player_stat in game.player_game_stats:
            points = stats_calculator.calculate_points(
                player_stat.total_ftm, player_stat.total_2pm, player_stat.total_3pm
            )
            if player_stat.player.team_id == game.playing_team_id:
                playing_team_score += points
            else:
                opponent_team_score += points

        game_list.append(
            {
                "id": game.id,
                "date": game.date.isoformat(),
                "home_team": {"id": game.playing_team.id, "name": game.playing_team.name},
                "away_team": {"id": game.opponent_team.id, "name": game.opponent_team.name},
                "home_score": playing_team_score,
                "away_score": opponent_team_score,
            }
        )

    return {"games": game_list}


@router.get("/v1/reports/box-score/{game_id}", response_model=dict[str, Any])
async def get_box_score_report(game_id: int, db: Annotated[Session, Depends(get_db)]):
    """Get box score report data."""
    game = crud_game.get_game_by_id(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    report_gen = ReportGenerator(db, stats_calculator)
    player_stats_list, game_summary = report_gen.get_game_box_score_data(game_id)

    # Transform data into expected format for API response
    # Group players by team
    home_players = []
    away_players = []
    home_totals = {
        "points": 0,
        "assists": 0,
        "rebounds": 0,
        "fg_made": 0,
        "fg_attempted": 0,
        "three_pt_made": 0,
        "three_pt_attempted": 0,
        "ft_made": 0,
        "ft_attempted": 0,
    }
    away_totals = {
        "points": 0,
        "assists": 0,
        "rebounds": 0,
        "fg_made": 0,
        "fg_attempted": 0,
        "three_pt_made": 0,
        "three_pt_attempted": 0,
        "ft_made": 0,
        "ft_attempted": 0,
    }

    for player_stat in player_stats_list:
        # Transform player stats to expected format
        player_data = {
            "name": player_stat.get("name", ""),
            "minutes": None,  # Not tracked
            "points": player_stat.get("points", 0),
            "assists": 0,  # Not tracked
            "rebounds": 0,  # Not tracked
            "fg_made": player_stat.get("fg2m", 0) + player_stat.get("fg3m", 0),
            "fg_attempted": player_stat.get("fg2a", 0) + player_stat.get("fg3a", 0),
            "fg_percentage": None,
            "three_pt_made": player_stat.get("fg3m", 0),
            "three_pt_attempted": player_stat.get("fg3a", 0),
            "three_pt_percentage": player_stat.get("fg3_pct"),
            "ft_made": player_stat.get("ftm", 0),
            "ft_attempted": player_stat.get("fta", 0),
            "ft_percentage": player_stat.get("ft_pct"),
            "plus_minus": None,  # Not tracked
        }

        # Calculate FG%
        if player_data["fg_attempted"] > 0:
            player_data["fg_percentage"] = (player_data["fg_made"] / player_data["fg_attempted"]) * 100

        # Add to appropriate team and update totals
        if player_stat.get("team") == game_summary.get("playing_team"):
            home_players.append(player_data)
            home_totals["points"] += player_data["points"]
            home_totals["assists"] += player_data["assists"]
            home_totals["rebounds"] += player_data["rebounds"]
            home_totals["fg_made"] += player_data["fg_made"]
            home_totals["fg_attempted"] += player_data["fg_attempted"]
            home_totals["three_pt_made"] += player_data["three_pt_made"]
            home_totals["three_pt_attempted"] += player_data["three_pt_attempted"]
            home_totals["ft_made"] += player_data["ft_made"]
            home_totals["ft_attempted"] += player_data["ft_attempted"]
        else:
            away_players.append(player_data)
            away_totals["points"] += player_data["points"]
            away_totals["assists"] += player_data["assists"]
            away_totals["rebounds"] += player_data["rebounds"]
            away_totals["fg_made"] += player_data["fg_made"]
            away_totals["fg_attempted"] += player_data["fg_attempted"]
            away_totals["three_pt_made"] += player_data["three_pt_made"]
            away_totals["three_pt_attempted"] += player_data["three_pt_attempted"]
            away_totals["ft_made"] += player_data["ft_made"]
            away_totals["ft_attempted"] += player_data["ft_attempted"]

    # Calculate team percentages
    if home_totals["fg_attempted"] > 0:
        home_totals["fg_percentage"] = (home_totals["fg_made"] / home_totals["fg_attempted"]) * 100
    else:
        home_totals["fg_percentage"] = None

    if home_totals["three_pt_attempted"] > 0:
        home_totals["three_pt_percentage"] = (home_totals["three_pt_made"] / home_totals["three_pt_attempted"]) * 100
    else:
        home_totals["three_pt_percentage"] = None

    if home_totals["ft_attempted"] > 0:
        home_totals["ft_percentage"] = (home_totals["ft_made"] / home_totals["ft_attempted"]) * 100
    else:
        home_totals["ft_percentage"] = None

    if away_totals["fg_attempted"] > 0:
        away_totals["fg_percentage"] = (away_totals["fg_made"] / away_totals["fg_attempted"]) * 100
    else:
        away_totals["fg_percentage"] = None

    if away_totals["three_pt_attempted"] > 0:
        away_totals["three_pt_percentage"] = (away_totals["three_pt_made"] / away_totals["three_pt_attempted"]) * 100
    else:
        away_totals["three_pt_percentage"] = None

    if away_totals["ft_attempted"] > 0:
        away_totals["ft_percentage"] = (away_totals["ft_made"] / away_totals["ft_attempted"]) * 100
    else:
        away_totals["ft_percentage"] = None

    # Build response
    return {
        "game_id": game_id,
        "game_date": game_summary.get("date", ""),
        "home_team": {
            "name": game_summary.get("playing_team", ""),
            "score": game_summary.get("team_points", 0),
            "players": home_players,
            "totals": home_totals,
            "quarter_scores": {},  # Not currently tracked quarter-by-quarter
        },
        "away_team": {
            "name": game_summary.get("opponent_team", ""),
            "score": away_totals["points"],  # Calculate from player totals
            "players": away_players,
            "totals": away_totals,
            "quarter_scores": {},  # Not currently tracked quarter-by-quarter
        },
    }


@router.get("/v1/reports/player-performance/{game_id}", response_model=dict[str, Any])
async def get_player_performance_report(game_id: int, db: Annotated[Session, Depends(get_db)]):
    """Get player performance report data."""
    game = crud_game.get_game_by_id(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    report_gen = ReportGenerator(db, stats_calculator)
    # Get all player stats for this game
    player_game_stats = crud_player_game_stats.get_player_game_stats_by_game(db, game_id)

    # Generate performance reports for all players
    player_reports = []
    for pgs in player_game_stats:
        try:
            report = report_gen.generate_player_performance_report(pgs.player_id, game_id)
            player_reports.append(report)
        except ValueError:
            # Skip players with no stats
            continue

    return {"game_id": game_id, "game_date": game.date.isoformat(), "players": player_reports}


@router.get("/v1/reports/team-efficiency/{game_id}", response_model=dict[str, Any])
async def get_team_efficiency_report(game_id: int, db: Annotated[Session, Depends(get_db)]):
    """Get team efficiency report data."""
    game = crud_game.get_game_by_id(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    report_gen = ReportGenerator(db, stats_calculator)
    # Generate efficiency reports for both teams
    playing_team_report = report_gen.generate_team_efficiency_report(game.playing_team_id, game_id)
    opponent_team_report = report_gen.generate_team_efficiency_report(game.opponent_team_id, game_id)

    return {
        "game_id": game_id,
        "game_date": game.date.isoformat(),
        "playing_team": playing_team_report,
        "opponent_team": opponent_team_report,
    }


@router.get("/v1/reports/scoring-analysis/{game_id}", response_model=dict[str, Any])
async def get_scoring_analysis_report(game_id: int, db: Annotated[Session, Depends(get_db)]):
    """Get scoring analysis report data."""
    game = crud_game.get_game_by_id(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    report_gen = ReportGenerator(db, stats_calculator)
    # Generate scoring analysis for both teams
    playing_team_analysis = report_gen.generate_scoring_analysis_report(game.playing_team_id, game_id)
    opponent_team_analysis = report_gen.generate_scoring_analysis_report(game.opponent_team_id, game_id)

    return {
        "game_id": game_id,
        "game_date": game.date.isoformat(),
        "playing_team": playing_team_analysis,
        "opponent_team": opponent_team_analysis,
    }


@router.get("/v1/reports/game-flow/{game_id}", response_model=dict[str, Any])
async def get_game_flow_report(game_id: int, db: Annotated[Session, Depends(get_db)]):
    """Get game flow report data."""
    game = crud_game.get_game_by_id(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    report_gen = ReportGenerator(db, stats_calculator)
    return report_gen.generate_game_flow_report(game_id)


@router.get("/v1/reports/player-season/{player_id}", response_model=dict[str, Any])
async def get_player_season_report(
    player_id: int,
    db: Annotated[Session, Depends(get_db)],
    season: Annotated[int | None, Query(description="Season year (e.g., 2024)")] = None,
):
    """Get player season statistics report."""
    player = crud_player.get_player_by_id(db, player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    # Convert season year to season string format
    season_str = f"{season}-{season + 1}" if season else None

    # Get player's season stats only if season_str is not None
    season_stats = None
    if season_str:
        season_stats = crud_player_season_stats.get_player_season_stats(db, player_id, season_str)

    if not season_stats and season:
        # Calculate season stats if not cached
        stats_service = SeasonStatsService(db)
        stats_service.update_player_season_stats(player_id, season_str)
        season_stats = (
            crud_player_season_stats.get_player_season_stats(db, player_id, season_str) if season_str else None
        )

    # Get all games for the player
    games = crud_game.get_all_games(db)
    # Filter for games where player participated
    player_games = []
    for game in games:
        if any(ps.player_id == player_id for ps in game.player_game_stats):
            player_games.append(game)
    games = player_games
    if season:
        games = [g for g in games if g.date.year == season]

    game_stats: list[dict[str, Any]] = []
    for game in sorted(games, key=lambda g: g.date):
        player_stats = next((ps for ps in game.player_game_stats if ps.player_id == player_id), None)
        if player_stats:
            points = stats_calculator.calculate_points(
                player_stats.total_ftm, player_stats.total_2pm, player_stats.total_3pm
            )
            assists = 0  # Not tracked in current model
            rebounds = 0  # Not tracked in current model

            game_stats.append(
                {
                    "game_id": game.id,
                    "date": game.date.isoformat(),
                    "opponent": (
                        game.opponent_team.name if game.playing_team_id == player.team_id else game.playing_team.name
                    ),
                    "points": points,
                    "assists": assists,
                    "rebounds": rebounds,
                    "fg_made": player_stats.total_2pm + player_stats.total_3pm,
                    "fg_attempted": player_stats.total_2pa + player_stats.total_3pa,
                    "three_pt_made": player_stats.total_3pm,
                    "three_pt_attempted": player_stats.total_3pa,
                    "ft_made": player_stats.total_ftm,
                    "ft_attempted": player_stats.total_fta,
                }
            )

    # Calculate season averages if no cached stats
    if season_stats:
        total_points_cached = stats_calculator.calculate_points(
            season_stats.total_ftm, season_stats.total_2pm, season_stats.total_3pm
        )
        ppg = total_points_cached / season_stats.games_played if season_stats.games_played > 0 else 0
        apg = 0  # Not tracked
        rpg = 0  # Not tracked
        fg_percentage = stats_calculator.calculate_percentage(
            season_stats.total_2pm + season_stats.total_3pm, season_stats.total_2pa + season_stats.total_3pa
        )
        three_pt_percentage = stats_calculator.calculate_percentage(season_stats.total_3pm, season_stats.total_3pa)
        ft_percentage = stats_calculator.calculate_percentage(season_stats.total_ftm, season_stats.total_fta)
        total_points = stats_calculator.calculate_points(
            season_stats.total_ftm, season_stats.total_2pm, season_stats.total_3pm
        )
    else:
        # Calculate from game stats
        total_points = sum(g["points"] for g in game_stats)  # type: ignore[misc]
        ppg = total_points / len(game_stats) if game_stats else 0
        apg = 0
        rpg = 0
        fg_percentage = stats_calculator.calculate_percentage(
            sum(g["fg_made"] for g in game_stats),  # type: ignore[misc]
            sum(g["fg_attempted"] for g in game_stats),  # type: ignore[misc]
        )
        three_pt_percentage = stats_calculator.calculate_percentage(
            sum(g["three_pt_made"] for g in game_stats),  # type: ignore[misc]
            sum(g["three_pt_attempted"] for g in game_stats),  # type: ignore[misc]
        )
        ft_percentage = stats_calculator.calculate_percentage(
            sum(g["ft_made"] for g in game_stats),  # type: ignore[misc]
            sum(g["ft_attempted"] for g in game_stats),  # type: ignore[misc]
        )

    return {
        "player": {
            "id": player.id,
            "name": player.name,
            "jersey_number": player.jersey_number,
            "position": player.position,
            "team": {"id": player.team.id, "name": player.team.name},
        },
        "season": season or "All",
        "season_stats": {
            "games_played": season_stats.games_played if season_stats else len(game_stats),
            "points": total_points
            if not season_stats
            else stats_calculator.calculate_points(
                season_stats.total_ftm, season_stats.total_2pm, season_stats.total_3pm
            ),
            "assists": 0,  # Not tracked
            "rebounds": 0,  # Not tracked
            "ppg": ppg,
            "apg": apg,
            "rpg": rpg,
            "fg_percentage": fg_percentage,
            "three_pt_percentage": three_pt_percentage,
            "ft_percentage": ft_percentage,
        },
        "game_log": game_stats,
    }


@router.get("/v1/reports/team-season/{team_id}", response_model=dict[str, Any])
async def get_team_season_report(
    team_id: int,
    db: Annotated[Session, Depends(get_db)],
    season: Annotated[int | None, Query(description="Season year (e.g., 2024)")] = None,
):
    """Get team season statistics report."""
    team = crud_team.get_team_by_id(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Convert season year to season string format
    season_str = f"{season}-{season + 1}" if season else None

    # Get team's season stats only if season_str is not None
    season_stats = None
    if season_str:
        season_stats = crud_team_season_stats.get_team_season_stats(db, team_id, season_str)

    if not season_stats and season:
        # Calculate season stats if not cached
        stats_service = SeasonStatsService(db)
        stats_service.update_team_season_stats(team_id, season_str)
        season_stats = crud_team_season_stats.get_team_season_stats(db, team_id, season_str) if season_str else None

    # Get all games for the team
    games = crud_game.get_games_by_team(db, team_id)
    if season:
        games = [g for g in games if g.date.year == season]

    # Calculate wins/losses
    wins = 0
    losses = 0
    total_points_for = 0
    total_points_against = 0

    for game in games:
        # Calculate scores
        playing_team_score = 0
        opponent_team_score = 0

        for player_stat in game.player_game_stats:
            points = stats_calculator.calculate_points(
                player_stat.total_ftm, player_stat.total_2pm, player_stat.total_3pm
            )
            if player_stat.player.team_id == game.playing_team_id:
                playing_team_score += points
            else:
                opponent_team_score += points

        # Determine if team won or lost
        if game.playing_team_id == team_id:
            total_points_for += playing_team_score
            total_points_against += opponent_team_score
            if playing_team_score > opponent_team_score:
                wins += 1
            else:
                losses += 1
        else:
            total_points_for += opponent_team_score
            total_points_against += playing_team_score
            if opponent_team_score > playing_team_score:
                wins += 1
            else:
                losses += 1

    # Get player season stats
    players = crud_player.get_players_by_team(db, team_id)
    player_stats: list[dict[str, Any]] = []

    for player in players:
        p_season_stats = (
            crud_player_season_stats.get_player_season_stats(db, player.id, season_str) if season_str else None
        )
        if p_season_stats and p_season_stats.games_played > 0:
            player_total_points = stats_calculator.calculate_points(
                p_season_stats.total_ftm, p_season_stats.total_2pm, p_season_stats.total_3pm
            )
            ppg = player_total_points / p_season_stats.games_played if p_season_stats.games_played > 0 else 0
            fg_percentage = stats_calculator.calculate_percentage(
                p_season_stats.total_2pm + p_season_stats.total_3pm, p_season_stats.total_2pa + p_season_stats.total_3pa
            )
            three_pt_percentage = stats_calculator.calculate_percentage(
                p_season_stats.total_3pm, p_season_stats.total_3pa
            )
            ft_percentage = stats_calculator.calculate_percentage(p_season_stats.total_ftm, p_season_stats.total_fta)

            player_stats.append(
                {
                    "player_id": player.id,
                    "name": player.name,
                    "jersey_number": player.jersey_number,
                    "position": player.position,
                    "games_played": p_season_stats.games_played,
                    "ppg": ppg,
                    "apg": 0,  # Not tracked
                    "rpg": 0,  # Not tracked
                    "fg_percentage": fg_percentage,
                    "three_pt_percentage": three_pt_percentage,
                    "ft_percentage": ft_percentage,
                }
            )

    # Sort player stats by PPG
    player_stats.sort(key=lambda x: x["ppg"], reverse=True)  # type: ignore[return-value]

    # Calculate team averages
    games_played = len(games)
    ppg = total_points_for / games_played if games_played > 0 else 0
    papg = total_points_against / games_played if games_played > 0 else 0

    # If we have cached season stats, use those for shooting percentages
    if season_stats:
        fg_percentage = stats_calculator.calculate_percentage(
            season_stats.total_2pm + season_stats.total_3pm, season_stats.total_2pa + season_stats.total_3pa
        )
        three_pt_percentage = stats_calculator.calculate_percentage(season_stats.total_3pm, season_stats.total_3pa)
        ft_percentage = stats_calculator.calculate_percentage(season_stats.total_ftm, season_stats.total_fta)
    else:
        # Calculate from all player stats
        total_fgm = sum(
            p["ppg"] * p["games_played"] * p["fg_percentage"] / 100  # type: ignore[operator]
            for p in player_stats
            if p["fg_percentage"] > 0  # type: ignore[operator]
        )
        total_fga = sum(p["ppg"] * p["games_played"] for p in player_stats)  # type: ignore[misc]
        fg_percentage = (total_fgm / total_fga * 100) if total_fga > 0 else 0
        three_pt_percentage = 0  # Would need to calculate from individual games
        ft_percentage = 0  # Would need to calculate from individual games

    return {
        "team": {"id": team.id, "name": team.name},
        "season": season or "All",
        "season_stats": {
            "games_played": games_played,
            "wins": wins,
            "losses": losses,
            "ppg": ppg,
            "papg": papg,
            "apg": 0,  # Not tracked
            "rpg": 0,  # Not tracked
            "fg_percentage": fg_percentage,
            "three_pt_percentage": three_pt_percentage,
            "ft_percentage": ft_percentage,
        },
        "player_stats": player_stats,
    }


@router.get("/v1/reports/export/{report_type}/{id}")
async def export_report(
    report_type: str,
    id: int,
    db: Annotated[Session, Depends(get_db)],
    format: Annotated[str, Query(regex="^(csv|json)$")] = "csv",
):
    """Export report data in various formats."""
    if report_type == "box-score":
        data = await get_box_score_report(id, db)
    elif report_type == "player-season":
        data = await get_player_season_report(id, db)
    elif report_type == "team-season":
        data = await get_team_season_report(id, db)
    else:
        raise HTTPException(status_code=400, detail="Invalid report type")

    if format == "csv":
        # Create CSV file
        output = io.StringIO()

        if report_type == "box-score":
            writer = csv.writer(output)
            # Write game info
            writer.writerow(["Game Report"])
            writer.writerow([])

            # Write team stats
            for team_type in ["home_team", "away_team"]:
                team_data = data.get(team_type)
                if team_data:
                    writer.writerow([team_data["name"]])
                    writer.writerow(["Player", "MIN", "PTS", "AST", "REB", "FG", "3PT", "FT"])

                    for player in team_data.get("players", []):
                        writer.writerow(
                            [
                                player["name"],
                                player.get("minutes", ""),
                                player["points"],
                                player.get("assists", 0),
                                player.get("rebounds", 0),
                                f"{player['fg_made']}/{player['fg_attempted']}",
                                f"{player['three_pt_made']}/{player['three_pt_attempted']}",
                                f"{player['ft_made']}/{player['ft_attempted']}",
                            ]
                        )
                    writer.writerow([])

        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={report_type}_{id}.csv"},
        )

    else:  # JSON format
        return data


@router.get("/reports/box-score/{game_id}", response_class=HTMLResponse)
async def view_box_score_report(request: Request, game_id: int, db: Annotated[Session, Depends(get_db)]):
    """Display box score report page."""
    game = crud_game.get_game_by_id(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    return templates.TemplateResponse("reports/box_score.html", {"request": request, "game_id": game_id, "game": game})


@router.get("/reports/player-season/{player_id}", response_class=HTMLResponse)
async def view_player_season_report(
    request: Request,
    player_id: int,
    db: Annotated[Session, Depends(get_db)],
    season: Annotated[int | None, Query()] = None,
):
    """Display player season report page."""
    player = crud_player.get_player_by_id(db, player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    return templates.TemplateResponse(
        "reports/player_season.html", {"request": request, "player_id": player_id, "player": player, "season": season}
    )


@router.get("/reports/team-season/{team_id}", response_class=HTMLResponse)
async def view_team_season_report(
    request: Request,
    team_id: int,
    db: Annotated[Session, Depends(get_db)],
    season: Annotated[int | None, Query()] = None,
):
    """Display team season report page."""
    team = crud_team.get_team_by_id(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    return templates.TemplateResponse(
        "reports/team_season.html", {"request": request, "team_id": team_id, "team": team, "season": season}
    )


@router.get("/reports/player-performance/{game_id}", response_class=HTMLResponse)
async def view_player_performance_report(request: Request, game_id: int, db: Annotated[Session, Depends(get_db)]):
    """Display player performance report page."""
    game = crud_game.get_game_by_id(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    return templates.TemplateResponse(
        "reports/player_performance.html", {"request": request, "game_id": game_id, "game": game}
    )
