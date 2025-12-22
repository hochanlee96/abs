from enum import Enum as PyEnum
from typing import List, Optional
from datetime import datetime

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, String, DateTime, func, ForeignKey, Integer, Boolean, Enum, JSON

class Base(DeclarativeBase):
    pass

class Role(str, PyEnum):
    USER = "USER"
    AI = "AI"

class MatchStatus(str, PyEnum):
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    FINISHED = "FINISHED"
    CANCELED = "CANCELED"

class InningHalf(str, PyEnum):
    TOP = "TOP"
    BOTTOM = "BOTTOM"

class ResultCode(str, PyEnum):
    STRIKEOUT = "STRIKEOUT"
    WALK = "WALK"
    SINGLE = "SINGLE"
    DOUBLE = "DOUBLE"
    TRIPLE = "TRIPLE"
    HOMERUN = "HOMERUN"
    OUT = "OUT"
    # Added for completeness if needed
    FLY_OUT = "FLY_OUT"
    GROUND_OUT = "GROUND_OUT"

class Account(Base):
    __tablename__ = "accounts"

    account_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    google_sub: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(3), server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(DateTime(3), server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    characters: Mapped[List["Character"]] = relationship(back_populates="owner")

class World(Base):
    __tablename__ = "worlds"

    world_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    world_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    teams: Mapped[List["Team"]] = relationship(back_populates="world")
    characters: Mapped[List["Character"]] = relationship(back_populates="world")
    matches: Mapped[List["Match"]] = relationship(back_populates="world")

class Team(Base):
    __tablename__ = "teams"

    team_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.world_id"), nullable=False)
    team_name: Mapped[str] = mapped_column(String(100), nullable=False)
    min_players: Mapped[int] = mapped_column(Integer, default=9)
    max_players: Mapped[int] = mapped_column(Integer, default=20)
    user_character_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True) # Leader or main character

    world: Mapped["World"] = relationship(back_populates="teams")
    team_players: Mapped[List["TeamPlayer"]] = relationship(back_populates="team")
    
    # Relationships for matches
    home_matches: Mapped[List["Match"]] = relationship(foreign_keys="[Match.home_team_id]", back_populates="home_team")
    away_matches: Mapped[List["Match"]] = relationship(foreign_keys="[Match.away_team_id]", back_populates="away_team")

class Character(Base):
    __tablename__ = "characters"

    character_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.world_id"), nullable=False)
    owner_account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("accounts.account_id"), nullable=True)
    is_user_created: Mapped[bool] = mapped_column(Boolean, default=False)
    nickname: Mapped[str] = mapped_column(String(100), nullable=False)
    contact: Mapped[int] = mapped_column(Integer, default=50)
    power: Mapped[int] = mapped_column(Integer, default=50)
    speed: Mapped[int] = mapped_column(Integer, default=50)

    # [Phase 2] Extended Stats
    mental: Mapped[int] = mapped_column(Integer, default=50)
    recovery: Mapped[int] = mapped_column(Integer, default=50)
    
    # Pitcher Specific
    stamina: Mapped[int] = mapped_column(Integer, default=100)
    velocity_max: Mapped[int] = mapped_column(Integer, default=140)
    pitch_fastball: Mapped[int] = mapped_column(Integer, default=0)
    pitch_slider: Mapped[int] = mapped_column(Integer, default=0)
    pitch_curve: Mapped[int] = mapped_column(Integer, default=0)
    pitch_changeup: Mapped[int] = mapped_column(Integer, default=0)
    pitch_splitter: Mapped[int] = mapped_column(Integer, default=0)
    
    # Batter Specific
    eye: Mapped[int] = mapped_column(Integer, default=50)
    clutch: Mapped[int] = mapped_column(Integer, default=50)
    contact_left: Mapped[int] = mapped_column(Integer, default=0)
    contact_right: Mapped[int] = mapped_column(Integer, default=0)
    power_left: Mapped[int] = mapped_column(Integer, default=0)
    power_right: Mapped[int] = mapped_column(Integer, default=0)
    
    # XP and Leveling (Added for Persistence)
    contact_xp: Mapped[int] = mapped_column(Integer, default=0)
    power_xp: Mapped[int] = mapped_column(Integer, default=0)
    speed_xp: Mapped[int] = mapped_column(Integer, default=0)
    
    # Cumulative Stats (Synced with Simulation)
    total_games: Mapped[int] = mapped_column(Integer, default=0)
    total_pa: Mapped[int] = mapped_column(Integer, default=0)
    total_ab: Mapped[int] = mapped_column(Integer, default=0)
    total_hits: Mapped[int] = mapped_column(Integer, default=0)
    total_homeruns: Mapped[int] = mapped_column(Integer, default=0)
    total_rbis: Mapped[int] = mapped_column(Integer, default=0)
    total_runs: Mapped[int] = mapped_column(Integer, default=0)
    total_bb: Mapped[int] = mapped_column(Integer, default=0)
    total_so: Mapped[int] = mapped_column(Integer, default=0)
    
    # Fielder Specific
    defense_range: Mapped[int] = mapped_column(Integer, default=50)
    defense_error: Mapped[int] = mapped_column(Integer, default=50)
    defense_arm: Mapped[int] = mapped_column(Integer, default=50)
    position_main: Mapped[str] = mapped_column(String(20), default="DH")
    position_sub: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    world: Mapped["World"] = relationship(back_populates="characters")
    owner: Mapped[Optional["Account"]] = relationship(back_populates="characters")
    team_players: Mapped[List["TeamPlayer"]] = relationship(back_populates="character")
    plate_appearances: Mapped[List["PlateAppearance"]] = relationship(back_populates="batter")
    training_sessions: Mapped[List["TrainingSession"]] = relationship(back_populates="character")

class TeamPlayer(Base):
    __tablename__ = "team_players"

    team_player_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.team_id"), nullable=False)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.character_id"), nullable=False)
    role: Mapped[Role] = mapped_column(Enum(Role), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    team: Mapped["Team"] = relationship(back_populates="team_players")
    character: Mapped["Character"] = relationship(back_populates="team_players")

class Match(Base):
    __tablename__ = "matches"

    match_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.world_id"), nullable=False)
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.team_id"), nullable=False)
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.team_id"), nullable=False)
    status: Mapped[MatchStatus] = mapped_column(Enum(MatchStatus), default=MatchStatus.SCHEDULED)
    home_score: Mapped[int] = mapped_column(Integer, default=0)
    away_score: Mapped[int] = mapped_column(Integer, default=0)
    game_state: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    winner_team_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    loser_team_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    
    match_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())

    world: Mapped["World"] = relationship(back_populates="matches")
    home_team: Mapped["Team"] = relationship(foreign_keys=[home_team_id], back_populates="home_matches")
    away_team: Mapped["Team"] = relationship(foreign_keys=[away_team_id], back_populates="away_matches")
    plate_appearances: Mapped[List["PlateAppearance"]] = relationship(back_populates="match")

class PlateAppearance(Base):
    __tablename__ = "plate_appearances"

    pa_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.match_id"), nullable=False)
    inning: Mapped[int] = mapped_column(Integer, nullable=False)
    half: Mapped[InningHalf] = mapped_column(Enum(InningHalf), nullable=False)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    batter_character_id: Mapped[int] = mapped_column(ForeignKey("characters.character_id"), nullable=False)
    result_code: Mapped[Optional[ResultCode]] = mapped_column(Enum(ResultCode), nullable=True)

    match: Mapped["Match"] = relationship(back_populates="plate_appearances")
    batter: Mapped["Character"] = relationship(back_populates="plate_appearances")

class Training(Base):
    __tablename__ = "trainings"

    training_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    train_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    contact_delta: Mapped[int] = mapped_column(Integer, default=0)
    power_delta: Mapped[int] = mapped_column(Integer, default=0)
    speed_delta: Mapped[int] = mapped_column(Integer, default=0)

    training_sessions: Mapped[List["TrainingSession"]] = relationship(back_populates="training")

class TrainingSession(Base):
    __tablename__ = "training_sessions"

    training_session_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.character_id"), nullable=False)
    training_id: Mapped[int] = mapped_column(ForeignKey("trainings.training_id"), nullable=False)
    
    performed_at: Mapped[datetime] = mapped_column(DateTime(3), server_default=func.current_timestamp())
    
    # Track exactly what was gained in this session
    applied_contact_delta: Mapped[int] = mapped_column(Integer, default=0)
    applied_power_delta: Mapped[int] = mapped_column(Integer, default=0)
    applied_speed_delta: Mapped[int] = mapped_column(Integer, default=0)
    
    xp_gained: Mapped[int] = mapped_column(Integer, default=0)
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False)

    character: Mapped["Character"] = relationship(back_populates="training_sessions")
    training: Mapped["Training"] = relationship(back_populates="training_sessions")