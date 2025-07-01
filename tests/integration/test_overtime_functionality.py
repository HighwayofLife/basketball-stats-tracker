"""Integration tests for overtime functionality."""

from datetime import date

from app.data_access.models import Game, Player, PlayerGameStats, PlayerQuarterStats, Team


class TestOvertimeFunctionality:
    """Test overtime game functionality across the system."""

    def test_game_with_overtime_stats(self, integration_db_session):
        """Test storing and retrieving overtime statistics."""
        import uuid

        # Create teams with unique names
        unique_suffix = str(uuid.uuid4())[:8]
        team_a = Team(name=f"OTLakers_{unique_suffix}", display_name=f"OT Lakers {unique_suffix}")
        team_b = Team(name=f"OTWarriors_{unique_suffix}", display_name=f"OT Warriors {unique_suffix}")
        integration_db_session.add_all([team_a, team_b])
        integration_db_session.flush()

        # Create players
        player_a1 = Player(name="LeBron James", team_id=team_a.id, jersey_number="23")
        player_b1 = Player(name="Stephen Curry", team_id=team_b.id, jersey_number="30")
        integration_db_session.add_all([player_a1, player_b1])
        integration_db_session.flush()

        # Create a game
        game = Game(
            date=date(2025, 7, 1),
            playing_team_id=team_a.id,
            opponent_team_id=team_b.id,
        )
        integration_db_session.add(game)
        integration_db_session.flush()

        # Create player game stats for an overtime game
        pgs_a1 = PlayerGameStats(
            game_id=game.id,
            player_id=player_a1.id,
            fouls=3,
            total_ftm=8,
            total_fta=10,
            total_2pm=5,
            total_2pa=10,
            total_3pm=2,
            total_3pa=6,
        )
        integration_db_session.add(pgs_a1)
        integration_db_session.flush()

        # Add quarter stats including overtime (quarters 5 and 6)
        quarters_data = [
            {"quarter": 1, "ftm": 2, "fta": 2, "fg2m": 1, "fg2a": 2, "fg3m": 0, "fg3a": 1},
            {"quarter": 2, "ftm": 2, "fta": 3, "fg2m": 2, "fg2a": 3, "fg3m": 1, "fg3a": 2},
            {"quarter": 3, "ftm": 1, "fta": 2, "fg2m": 1, "fg2a": 3, "fg3m": 0, "fg3a": 1},
            {"quarter": 4, "ftm": 2, "fta": 2, "fg2m": 1, "fg2a": 2, "fg3m": 1, "fg3a": 2},
            {"quarter": 5, "ftm": 1, "fta": 1, "fg2m": 0, "fg2a": 0, "fg3m": 0, "fg3a": 0},  # OT1
            {"quarter": 6, "ftm": 0, "fta": 0, "fg2m": 0, "fg2a": 0, "fg3m": 0, "fg3a": 0},  # OT2 (no shots)
        ]

        for q_data in quarters_data:
            pqs = PlayerQuarterStats(
                player_game_stat_id=pgs_a1.id,
                quarter_number=q_data["quarter"],
                ftm=q_data["ftm"],
                fta=q_data["fta"],
                fg2m=q_data["fg2m"],
                fg2a=q_data["fg2a"],
                fg3m=q_data["fg3m"],
                fg3a=q_data["fg3a"],
            )
            integration_db_session.add(pqs)

        integration_db_session.commit()

        # Verify we can retrieve overtime stats
        retrieved_stats = (
            integration_db_session.query(PlayerQuarterStats)
            .filter(PlayerQuarterStats.player_game_stat_id == pgs_a1.id)
            .order_by(PlayerQuarterStats.quarter_number)
            .all()
        )

        assert len(retrieved_stats) == 6
        assert retrieved_stats[4].quarter_number == 5  # OT1
        assert retrieved_stats[4].ftm == 1
        assert retrieved_stats[5].quarter_number == 6  # OT2
        assert retrieved_stats[5].ftm == 0

    def test_game_without_overtime_no_extra_quarters(self, integration_db_session):
        """Test that games without overtime only have 4 quarters."""
        import uuid

        # Create teams with unique names
        unique_suffix = str(uuid.uuid4())[:8]
        team_a = Team(name=f"OTCeltics_{unique_suffix}", display_name=f"OT Celtics {unique_suffix}")
        team_b = Team(name=f"OTHeat_{unique_suffix}", display_name=f"OT Heat {unique_suffix}")
        integration_db_session.add_all([team_a, team_b])
        integration_db_session.flush()

        # Create players
        player_a1 = Player(name="Jayson Tatum", team_id=team_a.id, jersey_number="0")
        integration_db_session.add(player_a1)
        integration_db_session.flush()

        # Create a game
        game = Game(
            date=date(2025, 7, 1),
            playing_team_id=team_a.id,
            opponent_team_id=team_b.id,
        )
        integration_db_session.add(game)
        integration_db_session.flush()

        # Create player game stats for a regular game (no overtime)
        pgs_a1 = PlayerGameStats(
            game_id=game.id,
            player_id=player_a1.id,
            fouls=2,
            total_ftm=6,
            total_fta=8,
            total_2pm=4,
            total_2pa=8,
            total_3pm=2,
            total_3pa=5,
        )
        integration_db_session.add(pgs_a1)
        integration_db_session.flush()

        # Add quarter stats for regular 4 quarters only
        for quarter in range(1, 5):
            pqs = PlayerQuarterStats(
                player_game_stat_id=pgs_a1.id,
                quarter_number=quarter,
                ftm=1,
                fta=2,
                fg2m=1,
                fg2a=2,
                fg3m=0 if quarter % 2 == 0 else 1,
                fg3a=1,
            )
            integration_db_session.add(pqs)

        integration_db_session.commit()

        # Verify only 4 quarters exist
        retrieved_stats = (
            integration_db_session.query(PlayerQuarterStats)
            .filter(PlayerQuarterStats.player_game_stat_id == pgs_a1.id)
            .all()
        )

        assert len(retrieved_stats) == 4
        assert all(stat.quarter_number <= 4 for stat in retrieved_stats)

    def test_overtime_csv_import_integration(self, integration_db_session):
        """Test CSV import with overtime data."""
        import uuid

        from app.schemas.csv_schemas import PlayerStatsRowSchema
        from app.services.import_services import ImportProcessor

        # Create teams with unique names
        unique_suffix = str(uuid.uuid4())[:8]
        team_a = Team(name=f"OTBulls_{unique_suffix}", display_name=f"OT Bulls {unique_suffix}")
        team_b = Team(name=f"OTNets_{unique_suffix}", display_name=f"OT Nets {unique_suffix}")
        integration_db_session.add_all([team_a, team_b])
        integration_db_session.flush()

        # Create players first
        player1 = Player(name="Zach LaVine", team_id=team_a.id, jersey_number="8")
        player2 = Player(name="Mikal Bridges", team_id=team_b.id, jersey_number="1")
        integration_db_session.add_all([player1, player2])
        integration_db_session.commit()

        # Create a game
        game = Game(
            date=date(2025, 7, 1),
            playing_team_id=team_a.id,
            opponent_team_id=team_b.id,
        )
        integration_db_session.add(game)
        integration_db_session.commit()

        # Import processor
        processor = ImportProcessor(integration_db_session)

        # Create player stats with overtime data
        player_stats = PlayerStatsRowSchema(
            TeamName=team_a.name,
            PlayerJersey="8",
            PlayerName="Zach LaVine",
            Fouls=4,
            QT1Shots="22-1x",
            QT2Shots="3/2",
            QT3Shots="22",
            QT4Shots="3/",
            OT1Shots="2/",  # Overtime 1
            OT2Shots="1x",  # Overtime 2
        )

        # Process the player stats
        success = processor._process_player_game_stats(game, player_stats)
        assert success is True

        # Verify overtime stats were created
        pgs = (
            integration_db_session.query(PlayerGameStats)
            .filter(
                PlayerGameStats.game_id == game.id,
                PlayerGameStats.player_id == player1.id,
            )
            .first()
        )
        assert pgs is not None

        quarter_stats = (
            integration_db_session.query(PlayerQuarterStats)
            .filter(PlayerQuarterStats.player_game_stat_id == pgs.id)
            .order_by(PlayerQuarterStats.quarter_number)
            .all()
        )

        # Should have 6 quarters
        assert len(quarter_stats) == 6

        # Check OT1 (quarter 5) - "2/" means 1 made 2-pointer + 1 missed 3-pointer
        ot1 = next(q for q in quarter_stats if q.quarter_number == 5)
        assert ot1.fg2m == 1  # "2" means 1 made 2-pointer
        assert ot1.fg2a == 1  # 1 attempt
        assert ot1.fg3m == 0  # "/" means missed 3-pointer
        assert ot1.fg3a == 1  # 1 attempt

        # Check OT2 (quarter 6) - "1x" means 1 made FT + 1 missed FT
        ot2 = next(q for q in quarter_stats if q.quarter_number == 6)
        assert ot2.ftm == 1  # "1" means 1 made FT
        assert ot2.fta == 2  # "1x" means 1 made + 1 missed = 2 total FT attempts

    # TODO: Fix session isolation issue in API test - commenting out for now
    # def test_overtime_box_score_api(self, authenticated_client, integration_db_session):
    #     """Test that box score API correctly returns overtime data."""
    #     pass

    def test_game_detail_page_overtime_display(self, authenticated_client, integration_db_session):
        """Test that game detail page correctly displays overtime."""
        import uuid

        # Create teams with unique names
        unique_suffix = str(uuid.uuid4())[:8]
        team_a = Team(name=f"OTSpurs_{unique_suffix}", display_name=f"OT Spurs {unique_suffix}")
        team_b = Team(name=f"OTClippers_{unique_suffix}", display_name=f"OT Clippers {unique_suffix}")
        integration_db_session.add_all([team_a, team_b])
        integration_db_session.flush()

        # Create a game
        game = Game(
            date=date(2025, 7, 1),
            playing_team_id=team_a.id,
            opponent_team_id=team_b.id,
        )
        integration_db_session.add(game)
        integration_db_session.commit()

        # Access game detail page
        response = authenticated_client.get(f"/games/{game.id}")
        assert response.status_code == 200

        # The page should have JavaScript that dynamically creates overtime columns
        assert "createScoreboard" in response.text
        assert "quarter_scores" in response.text
