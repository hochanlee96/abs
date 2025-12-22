from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc
from typing import List, Optional
from .models import World, Team, Character, Match, TeamPlayer, Role, MatchStatus, Training, TrainingSession, InningHalf

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
    speed: int = 0,
    # [Phase 2]
    mental: int = 50,
    recovery: int = 50,
    stamina: int = 100,
    velocity_max: int = 140,
    pitch_fastball: int = 0,
    pitch_slider: int = 0,
    pitch_curve: int = 0,
    pitch_changeup: int = 0,
    pitch_splitter: int = 0,
    eye: int = 50,
    clutch: int = 50,
    contact_left: int = 0,
    contact_right: int = 0,
    power_left: int = 0,
    power_right: int = 0,
    defense_range: int = 50,
    defense_error: int = 50,
    defense_arm: int = 50,
    position_main: str = "DH",
    position_sub: Optional[str] = None
) -> Character:
    char = Character(
        world_id=world_id, 
        nickname=nickname, 
        owner_account_id=owner_account_id, 
        is_user_created=is_user_created,
        contact=contact,
        power=power,
        speed=speed,
        # [Phase 2]
        mental=mental,
        recovery=recovery,
        stamina=stamina,
        velocity_max=velocity_max,
        pitch_fastball=pitch_fastball,
        pitch_slider=pitch_slider,
        pitch_curve=pitch_curve,
        pitch_changeup=pitch_changeup,
        pitch_splitter=pitch_splitter,
        eye=eye,
        clutch=clutch,
        contact_left=contact_left,
        contact_right=contact_right,
        power_left=power_left,
        power_right=power_right,
        defense_range=defense_range,
        defense_error=defense_error,
        defense_arm=defense_arm,
        position_main=position_main,
        position_sub=position_sub
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

def perform_training(db: Session, character_id: int, training_id: int) -> dict:
    character = get_character(db, character_id)
    training = db.execute(select(Training).where(Training.training_id == training_id)).scalar_one_or_none()

    if not character or not training:
        return {"success": False, "error": "Character or Training not found"}

    # 1. Check Training Limit
    # Get last training session for this character
    last_session = db.execute(
        select(TrainingSession)
        .where(TrainingSession.character_id == character_id)
        .order_by(desc(TrainingSession.performed_at))
        .limit(1)
    ).scalar_one_or_none()

    # Get last finished match in this world
    last_match = db.execute(
        select(Match)
        .where(Match.world_id == character.world_id)
        .where(Match.status == MatchStatus.FINISHED)
        .order_by(desc(Match.finished_at))
        .limit(1)
    ).scalar_one_or_none()

    # Logic: Lock if (last_session exists) AND (no matches finished OR last_session is newer than last_match)
    is_locked = False
    if last_session:
        if not last_match or last_session.performed_at > last_match.finished_at:
            is_locked = True

    if is_locked:
        return {"success": False, "error": "Run a game before continuing training"}

    # 2. Randomize XP gain (10-35)
    import random
    base_xp = random.randint(10, 35)
    is_critical = random.random() < 0.2
    xp_gained = base_xp * (2 if is_critical else 1)

    # 3. Apply XP and handle Level Up
    # Determine which stat type to update based on training deltas
    # (Simple mapping: whichever is > 0)
    stat_type = "contact"
    if training.power_delta > 0: stat_type = "power"
    elif training.speed_delta > 0: stat_type = "speed"

    current_xp_field = f"{stat_type}_xp"
    current_level_field = stat_type
    
    current_xp = getattr(character, current_xp_field)
    current_level = getattr(character, current_level_field)
    
    current_xp += xp_gained
    xp_needed = current_level * 50
    
    leveled_up = False
    while current_xp >= xp_needed:
        current_xp -= xp_needed
        current_level += 1
        xp_needed = current_level * 50
        leveled_up = True
        
    setattr(character, current_xp_field, current_xp)
    setattr(character, current_level_field, current_level)

    # 4. Create session log
    session = TrainingSession(
        character_id=character_id, 
        training_id=training_id,
        applied_contact_delta=training.contact_delta if leveled_up and stat_type == "contact" else 0,
        applied_power_delta=training.power_delta if leveled_up and stat_type == "power" else 0,
        applied_speed_delta=training.speed_delta if leveled_up and stat_type == "speed" else 0,
        xp_gained=xp_gained,
        is_critical=is_critical
    )
    db.add(session)
    db.commit()
    db.refresh(character)
    
    return {
        "success": True,
        "character": character,
        "xp_gained": xp_gained,
        "is_critical": is_critical,
        "leveled_up": leveled_up,
        "new_level": current_level if leveled_up else None
    }

def get_training_status(db: Session, character_id: int) -> dict:
    character = get_character(db, character_id)
    if not character:
        return {"is_locked": False, "reason": "Character not found"}

    last_session = db.execute(
        select(TrainingSession)
        .where(TrainingSession.character_id == character_id)
        .order_by(desc(TrainingSession.performed_at))
        .limit(1)
    ).scalar_one_or_none()

    last_match = db.execute(
        select(Match)
        .where(Match.world_id == character.world_id)
        .where(Match.status == MatchStatus.FINISHED)
        .order_by(desc(Match.finished_at))
        .limit(1)
    ).scalar_one_or_none()

    is_locked = False
    if last_session:
        if not last_match or last_session.performed_at > last_match.finished_at:
            is_locked = True

    return {
        "is_locked": is_locked,
        "reason": "Run a game before continuing training" if is_locked else None,
        "last_training": last_session.performed_at if last_session else None,
        "last_match": last_match.finished_at if last_match else None
    }
