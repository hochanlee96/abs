from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..db import get_db
from .. import crud_stats

router = APIRouter()

class CharacterStats(BaseModel):
    games_played: int
    at_bats: int
    hits: int
    homeruns: int
    rbis: int
    batting_average: float

@router.get("/characters/{character_id}/stats", response_model=CharacterStats)
def get_character_stats(character_id: int, db: Session = Depends(get_db)):
    stats = crud_stats.get_character_stats(db, character_id)
    return stats
