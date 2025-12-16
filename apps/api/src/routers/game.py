from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from ..db import get_db
from .. import crud_game
from ..models import MatchStatus
from ..auth_google import verify_google_id_token_from_header
from ..crud_accounts import upsert_account_from_google

router = APIRouter()

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

class MatchCreate(BaseModel):
    world_id: int
    home_team_id: int
    away_team_id: int

class TrainingPerform(BaseModel):
    training_id: int

@router.post("/characters")
def create_character(char: CharacterCreate, db: Session = Depends(get_db)):
    if char.is_user_created:
        total_points = char.contact + char.power + char.speed
        if total_points != 10:
            raise HTTPException(status_code=400, detail="Total stat points must be exactly 10")
            
    return crud_game.create_character(
        db, 
        char.world_id, 
        char.nickname, 
        char.owner_account_id, 
        char.is_user_created,
        char.contact,
        char.power,
        char.speed
    )

@router.get("/characters/{character_id}")
def get_character(character_id: int, db: Session = Depends(get_db)):
    char = crud_game.get_character(db, character_id)
    if not char:
        raise HTTPException(status_code=404, detail="Character not found")
    return char

@router.post("/matches")
def create_match(match: MatchCreate, db: Session = Depends(get_db)):
    return crud_game.create_match(db, match.world_id, match.home_team_id, match.away_team_id)

@router.get("/matches/{match_id}")
def get_match(match_id: int, db: Session = Depends(get_db)):
    match = crud_game.get_match(db, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return match

@router.get("/trainings")
def list_trainings(db: Session = Depends(get_db)):
    return crud_game.get_trainings(db)

@router.post("/characters/{character_id}/train")
def perform_training(character_id: int, body: TrainingPerform, db: Session = Depends(get_db)):
    char = crud_game.perform_training(db, character_id, body.training_id)
    if not char:
        raise HTTPException(status_code=400, detail="Training failed (Character or Training not found)")
    return char

@router.get("/me/characters")
def list_my_characters(db: Session = Depends(get_db), payload: dict = Depends(verify_google_id_token_from_header)):
    acc = upsert_account_from_google(db, payload)
    return crud_game.get_characters_by_account(db, acc.account_id)
