from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Header
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from ..db import get_db
from .. import crud_game
from .. import models as db_models
from ..models import MatchStatus
from ..auth_google import verify_google_id_token_from_header
from ..crud_accounts import upsert_account_from_google
from ..simulation_runner import run_match_background

router = APIRouter()

def get_auth_payload(authorization: str | None = Header(default=None)):
    return verify_google_id_token_from_header(authorization)

# Pydantic models for request body
class WorldCreate(BaseModel):
    world_name: str

class TeamCreate(BaseModel):
    world_id: int
    team_name: str
    user_character_id: Optional[int] = None

class CharacterCreate(BaseModel):
    world_id: int
    nickname: str
    owner_account_id: Optional[int] = None
    is_user_created: bool = False
    contact: int = 0
    power: int = 0
    speed: int = 0
    # [Phase 2]
    mental: int = 50
    recovery: int = 50
    stamina: int = 100
    velocity_max: int = 140
    pitch_fastball: int = 0
    pitch_slider: int = 0
    pitch_curve: int = 0
    pitch_changeup: int = 0
    pitch_splitter: int = 0
    eye: int = 50
    clutch: int = 50
    contact_left: int = 0
    contact_right: int = 0
    power_left: int = 0
    power_right: int = 0
    defense_range: int = 50
    defense_error: int = 50
    defense_arm: int = 50
    position_main: str = "DH"
    position_sub: Optional[str] = None

class MatchCreate(BaseModel):
    world_id: int
    home_team_id: int
    away_team_id: int

class TrainingPerform(BaseModel):
    training_id: int

@router.post("/worlds")
def create_world(world: WorldCreate, db: Session = Depends(get_db)):
    return crud_game.create_world(db, world.world_name)

@router.get("/worlds")
def list_worlds(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud_game.get_worlds(db, skip, limit)

@router.post("/teams")
def create_team(team: TeamCreate, db: Session = Depends(get_db)):
    return crud_game.create_team(db, team.world_id, team.team_name, team.user_character_id)

@router.get("/teams/{team_id}")
def get_team(team_id: int, db: Session = Depends(get_db)):
    team = crud_game.get_team(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team

@router.get("/worlds/{world_id}/teams")
def list_world_teams(world_id: int, db: Session = Depends(get_db)):
    return crud_game.get_teams_by_world(db, world_id)

@router.get("/worlds/{world_id}/matches")
def list_world_matches(world_id: int, db: Session = Depends(get_db)):
    return crud_game.get_matches_by_world(db, world_id)

@router.post("/characters")
def create_character(char: CharacterCreate, db: Session = Depends(get_db), payload: dict = Depends(get_auth_payload)):
    # Upsert account to ensure it exists and get ID
    acc = upsert_account_from_google(db, payload)
    
    if char.is_user_created:
        total_points = char.contact + char.power + char.speed
        if total_points != 10:
            raise HTTPException(status_code=400, detail="Total stat points must be exactly 10")
            
    return crud_game.create_character(
        db, 
        char.world_id, 
        char.nickname, 
        acc.account_id, # Enforce ownership
        char.is_user_created,
        char.contact,
        char.power,
        char.speed,
        # [Phase 2]
        mental=char.mental,
        recovery=char.recovery,
        stamina=char.stamina,
        velocity_max=char.velocity_max,
        pitch_fastball=char.pitch_fastball,
        pitch_slider=char.pitch_slider,
        pitch_curve=char.pitch_curve,
        pitch_changeup=char.pitch_changeup,
        pitch_splitter=char.pitch_splitter,
        eye=char.eye,
        clutch=char.clutch,
        contact_left=char.contact_left,
        contact_right=char.contact_right,
        power_left=char.power_left,
        power_right=char.power_right,
        defense_range=char.defense_range,
        defense_error=char.defense_error,
        defense_arm=char.defense_arm,
        position_main=char.position_main,
        position_sub=char.position_sub
    )

@router.get("/characters/{character_id}")
def get_character(character_id: int, db: Session = Depends(get_db)):
    char = crud_game.get_character(db, character_id)
    if not char:
        raise HTTPException(status_code=404, detail="Character not found")
    return char

@router.delete("/characters/{character_id}")
def delete_character(character_id: int, db: Session = Depends(get_db), payload: dict = Depends(get_auth_payload)):
    # Optional: Verify ownership
    acc = upsert_account_from_google(db, payload)
    char = crud_game.get_character(db, character_id)
    if not char:
        raise HTTPException(status_code=404, detail="Character not found")
    if char.owner_account_id != acc.account_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this character")
        
    success = crud_game.delete_character(db, character_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete character")
    return {"status": "success"}

@router.post("/matches")
def create_match(match: MatchCreate, db: Session = Depends(get_db)):
    return crud_game.create_match(db, match.world_id, match.home_team_id, match.away_team_id)

from .. import schemas

@router.get("/matches/{match_id}", response_model=schemas.MatchSchema)
def get_match(match_id: int, db: Session = Depends(get_db)):
    match = crud_game.get_match(db, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return match

class PlayRequest(BaseModel):
    world_id: Optional[int] = None

@router.post("/play")
def play_match(body: PlayRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db), payload: dict = Depends(get_auth_payload)):
    """
    Finds the next SCHEDULED match for the USER's team and starts the simulation in background.
    """
    # 0. Redundant Alias for robust scope (belt and suspenders)
    Character = db_models.Character
    TeamPlayer = db_models.TeamPlayer
    
    # 1. Identify User and their Team
    acc = upsert_account_from_google(db, payload)
    # Get the user's first character in this world (or any character they own)
    char = db.query(db_models.Character).filter_by(owner_account_id=acc.account_id).first()
    if not char:
        raise HTTPException(status_code=404, detail="No character found for user")
    
    # Get user's team
    team_player = db.query(db_models.TeamPlayer).filter_by(character_id=char.character_id).first()
    if not team_player:
        raise HTTPException(status_code=404, detail="User character is not on a team")
    
    user_team_id = team_player.team_id
    
    # 2. Find any NPC matches scheduled BEFORE the user's next match
    # We want to clear the queue so the league progresses.
    # Logic: Get the very next scheduled match in the world.
    # If it doesn't involve the user, mark it as SIMULATED (Finished) and move on.
    
    # Limit to e.g. 5 skips to avoid infinite loops or massive jumps
    skipped_count = 0
    while skipped_count < 10:
        next_global_match = crud_game.get_next_scheduled_match(db, body.world_id)
        if not next_global_match:
            break
            
        if next_global_match.home_team_id == user_team_id or next_global_match.away_team_id == user_team_id:
            # Found user match!
            break
        
        # Skip this NPC-only match (Mark as finished)
        next_global_match.status = MatchStatus.FINISHED
        # Assign a random score 1-5 for flavor
        import random
        next_global_match.home_score = random.randint(0, 5)
        next_global_match.away_score = random.randint(0, 5)
        # Record who won
        if next_global_match.home_score > next_global_match.away_score:
            next_global_match.winner_team_id = next_global_match.home_team_id
            next_global_match.loser_team_id = next_global_match.away_team_id
        else:
            next_global_match.winner_team_id = next_global_match.away_team_id
            next_global_match.loser_team_id = next_global_match.home_team_id
            
        db.add(next_global_match)
        db.commit()
        skipped_count += 1
    
    # 3. Now get the User's next match
    match = crud_game.get_next_scheduled_match(db, body.world_id, team_id=user_team_id)
    if not match:
        raise HTTPException(status_code=404, detail="No more scheduled matches found for your team.")
    
    # 4. Start Background Task
    background_tasks.add_task(run_match_background, match.match_id)
    
    return {
        "status": "started", 
        "match_id": match.match_id, 
        "message": f"Simulation started for your team! (Skipped {skipped_count} NPC games)",
        "skipped": skipped_count
    }


@router.get("/trainings")
def list_trainings(db: Session = Depends(get_db)):
    return crud_game.get_trainings(db)

@router.post("/characters/{character_id}/train")
def perform_training(character_id: int, body: TrainingPerform, db: Session = Depends(get_db)):
    result = crud_game.perform_training(db, character_id, body.training_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.get("/characters/{character_id}/training-status")
def get_training_status(character_id: int, db: Session = Depends(get_db)):
    return crud_game.get_training_status(db, character_id)

@router.get("/me/characters")
def list_my_characters(db: Session = Depends(get_db), payload: dict = Depends(get_auth_payload)):
    acc = upsert_account_from_google(db, payload)
    return crud_game.get_characters_by_account(db, acc.account_id)

class LeagueInit(BaseModel):
    user_character_id: int
    world_name: str = "My New League"

@router.post("/league/init")
def init_league(body: LeagueInit, db: Session = Depends(get_db)):
    from ..services import league_generator
    try:
        result = league_generator.generate_league(db, body.user_character_id, body.world_name)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Log error in real app
        print(f"League generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate league")
