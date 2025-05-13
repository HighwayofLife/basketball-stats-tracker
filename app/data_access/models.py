# pylint: disable=R0903  # Too few public methods
"""SQLAlchemy ORM models for the basketball stats application."""

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for SQLAlchemy model definitions."""
    pass


class Team(Base):
    """Represents a basketball team in the league."""
    __tablename__ = 'teams'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    players: Mapped[list["Player"]] = relationship(
        'Player', back_populates='team', cascade='all, delete-orphan'
    )
    home_games: Mapped[list["Game"]] = relationship(
        'Game', back_populates='playing_team', foreign_keys='Game.playing_team_id'
    )
    away_games: Mapped[list["Game"]] = relationship(
        'Game', back_populates='opponent_team', foreign_keys='Game.opponent_team_id'
    )

    def __repr__(self):
        return f"<Team(id={self.id}, name='{self.name}')>"

class Player(Base):
    """Represents a player in a team."""
    __tablename__ = 'players'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey('teams.id'), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    jersey_number: Mapped[int] = mapped_column(Integer, nullable=False)

    team: Mapped["Team"] = relationship('Team', back_populates='players')
    game_stats: Mapped[list["PlayerGameStats"]] = relationship(
        'PlayerGameStats', back_populates='player', cascade='all, delete-orphan'
    )

    __table_args__ = (
        UniqueConstraint('team_id', 'jersey_number', name='uq_player_team_jersey'),
        UniqueConstraint('team_id', 'name', name='uq_player_team_name'),
    )

    def __repr__(self):
        return (
            f"<Player(id={self.id}, name='{self.name}', "
            f"jersey_number={self.jersey_number}, team_id={self.team_id})>"
        )

class Game(Base):
    """Represents a game played between two teams."""
    __tablename__ = 'games'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[str] = mapped_column(String, nullable=False)  # Could use Date type if preferred
    playing_team_id: Mapped[int] = mapped_column(Integer, ForeignKey('teams.id'), nullable=False)
    opponent_team_id: Mapped[int] = mapped_column(Integer, ForeignKey('teams.id'), nullable=False)

    playing_team: Mapped["Team"] = relationship(
        'Team', back_populates='home_games', foreign_keys=[playing_team_id]
    )
    opponent_team: Mapped["Team"] = relationship(
        'Team', back_populates='away_games', foreign_keys=[opponent_team_id]
    )
    player_game_stats: Mapped[list["PlayerGameStats"]] = relationship(
        'PlayerGameStats', back_populates='game', cascade='all, delete-orphan'
    )

    def __repr__(self):
        return (
            f"<Game(id={self.id}, date='{self.date}', "
            f"playing_team_id={self.playing_team_id}, "
            f"opponent_team_id={self.opponent_team_id})>"
        )

class PlayerGameStats(Base):
    """Represents the overall statistics for a player in a specific game."""
    __tablename__ = 'player_game_stats'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[int] = mapped_column(Integer, ForeignKey('games.id'), nullable=False)
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey('players.id'), nullable=False)
    fouls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_ftm: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_fta: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_2pm: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_2pa: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_3pm: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_3pa: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    game: Mapped["Game"] = relationship('Game', back_populates='player_game_stats')
    player: Mapped["Player"] = relationship('Player', back_populates='game_stats')
    quarter_stats: Mapped[list["PlayerQuarterStats"]] = relationship(
        'PlayerQuarterStats', back_populates='player_game_stat', cascade='all, delete-orphan'
    )

    __table_args__ = (
        UniqueConstraint('game_id', 'player_id', name='uq_player_game'),
    )

    def __repr__(self):
        return (
            f"<PlayerGameStats(id={self.id}, game_id={self.game_id}, "
            f"player_id={self.player_id}, fouls={self.fouls}, "
            f"FTM={self.total_ftm}, FTA={self.total_fta}, "
            f"2PM={self.total_2pm}, 2PA={self.total_2pa}, "
            f"3PM={self.total_3pm}, 3PA={self.total_3pa})>"
        )

class PlayerQuarterStats(Base):
    """Represents the statistics for a player in a specific quarter of a game."""
    __tablename__ = 'player_quarter_stats'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_game_stat_id: Mapped[int] = mapped_column(Integer, ForeignKey('player_game_stats.id'), nullable=False)
    quarter_number: Mapped[int] = mapped_column(Integer, nullable=False)
    ftm: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fta: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fg2m: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fg2a: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fg3m: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fg3a: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    player_game_stat: Mapped["PlayerGameStats"] = relationship(
        'PlayerGameStats', back_populates='quarter_stats'
    )

    __table_args__ = (
        UniqueConstraint('player_game_stat_id', 'quarter_number', name='uq_player_game_quarter'),
        CheckConstraint('quarter_number >= 1 AND quarter_number <= 4', name='check_quarter_number'),
    )

    def __repr__(self):
        return (
            f"<PlayerQuarterStats(id={self.id}, "
            f"player_game_stat_id={self.player_game_stat_id}, "
            f"quarter={self.quarter_number}, FTM={self.ftm}, FTA={self.fta}, "
            f"FG2M={self.fg2m}, FG2A={self.fg2a}, FG3M={self.fg3m}, FG3A={self.fg3a})>"
        )
