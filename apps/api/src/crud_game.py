from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional
from .models import World, Team, Character, Match, TeamPlayer, Role, MatchStatus, Training, TrainingSession

# World
def create_world(db: Session, world_name: str) -> World:
    world = World(world_name=world_name)
    db.add(world)
    db.commit()
    db.refresh(world)
    return world

def get_worlds(db: Session, skip: int = 0, limit: int = 100) -> List[World]:
    return db.execute(select(World).offset(skip).limit(limit)).scalars().all()

def get_world(db: Session, world_id: int) -> Optional[World]:
    return db.execute(select(World).where(World.world_id == world_id)).scalar_one_or_none()

# Team
def create_team(db: Session, world_id: int, team_name: str, user_character_id: Optional[int] = None) -> Team:
    team = Team(world_id=world_id, team_name=team_name, user_character_id=user_character_id)
    db.add(team)
    db.commit()
    db.refresh(team)
    return team

def get_teams(db: Session, world_id: int, skip: int = 0, limit: int = 100) -> List[Team]:
    return db.execute(select(Team).where(Team.world_id == world_id).offset(skip).limit(limit)).scalars().all()

def get_team(db: Session, team_id: int) -> Optional[Team]:
    return db.execute(select(Team).where(Team.team_id == team_id)).scalar_one_or_none()

# Character
def create_character(
    db: Session, 
    world_id: int, 
    nickname: str, 
    owner_account_id: Optional[int] = None, 
    is_user_created: bool = False,
    contact: int = 0,
    power: int = 0,
    speed: int = 0
) -> Character:
    char = Character(
        world_id=world_id, 
        nickname=nickname, 
        owner_account_id=owner_account_id, 
        is_user_created=is_user_created,
        contact=contact,
        power=power,
        speed=speed
    )
    db.add(char)
    db.commit()
    db.refresh(char)
    return char

def get_character(db: Session, character_id: int) -> Optional[Character]:
    return db.execute(select(Character).where(Character.character_id == character_id)).scalar_one_or_none()

def get_characters_by_account(db: Session, account_id: int) -> List[Character]:
    return db.execute(select(Character).where(Character.owner_account_id == account_id).order_by(Character.character_id.desc())).scalars().all()

def get_teams_by_world(db: Session, world_id: int) -> List[Team]:
    return db.execute(select(Team).where(Team.world_id == world_id)).scalars().all()

def get_matches_by_world(db: Session, world_id: int) -> List[Match]:
    return db.execute(select(Match).where(Match.world_id == world_id)).scalars().all()

def delete_character(db: Session, character_id: int) -> bool:
    char = get_character(db, character_id)
    if char:
        # Cascade delete world if this character belongs to one
        # Logic: If this is the user's main character, we assume they want to wipe the league instance.
        if char.world_id:
            delete_world(db, char.world_id)
        else:
            db.delete(char)
            db.commit()
        return True
    return False

def delete_world(db: Session, world_id: int):
    # 1. Delete Matches
    db.execute(select(Match).where(Match.world_id == world_id)).scalars().all()
    # SQL Alchemy specific bulk delete or iterate
    # For simplicity and relationship handling, proper queries:
    
    # Matches
    db.query(Match).filter(Match.world_id == world_id).delete()
    
    # TeamPlayers (Need to find teams first or join)
    # db.query(TeamPlayer).filter(TeamPlayer.team.has(world_id=world_id)) ...
    # Easier to iterate teams
    teams = get_teams(db, world_id)
    for team in teams:
        db.query(TeamPlayer).filter(TeamPlayer.team_id == team.team_id).delete()
        
    # Teams
    db.query(Team).filter(Team.world_id == world_id).delete()
    
    # Characters (NPCs and the User Char itself if not already deleted)
    # delete_character calls this, so char is still in DB session?
    # We should delete all characters in this world.
    db.query(Character).filter(Character.world_id == world_id).delete()
    
    # World
    db.query(World).filter(World.world_id == world_id).delete()
    
    db.commit()

# Match
def create_match(db: Session, world_id: int, home_team_id: int, away_team_id: int) -> Match:
    match = Match(
        world_id=world_id, 
        home_team_id=home_team_id, 
        away_team_id=away_team_id, 
        status=MatchStatus.SCHEDULED
    )
    db.add(match)
    db.commit()
    db.refresh(match)
    return match

def get_match(db: Session, match_id: int) -> Optional[Match]:
    return db.execute(select(Match).where(Match.match_id == match_id)).scalar_one_or_none()

def get_next_scheduled_match(db: Session, world_id: Optional[int] = None) -> Optional[Match]:
    query = select(Match).where(Match.status == MatchStatus.SCHEDULED)
    if world_id:
        query = query.where(Match.world_id == world_id)
    return db.execute(query.limit(1)).scalar_one_or_none()

def update_match_status(db: Session, match_id: int, status: MatchStatus) -> Optional[Match]:
    match = get_match(db, match_id)
    if match:
        match.status = status
        db.commit()
        db.refresh(match)
    return match


# Training
def create_training(db: Session, train_name: str, contact_delta: int = 0, power_delta: int = 0, speed_delta: int = 0) -> Training:
    training = Training(
        train_name=train_name,
        contact_delta=contact_delta,
        power_delta=power_delta,
        speed_delta=speed_delta
    )
    db.add(training)
    db.commit()
    db.refresh(training)
    return training

def get_trainings(db: Session) -> List[Training]:
    return db.execute(select(Training)).scalars().all()

def perform_training(db: Session, character_id: int, training_id: int) -> Optional[Character]:
    character = get_character(db, character_id)
    training = db.execute(select(Training).where(Training.training_id == training_id)).scalar_one_or_none()

    if not character or not training:
        return None

    # Create session
    session = TrainingSession(character_id=character_id, training_id=training_id)
    db.add(session)

    # Update stats
    character.contact += training.contact_delta
    character.power += training.power_delta
    character.speed += training.speed_delta

    db.commit()
    db.refresh(character)
    return character
