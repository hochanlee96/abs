from sqlalchemy.orm import Session
from sqlalchemy import select
from .models import PlateAppearance, ResultCode, Character

def get_character_stats(db: Session, character_id: int) -> dict:
    char = db.query(Character).filter_by(character_id=character_id).first()
    if not char:
        return {}
    
    # Calculate Average
    avg = char.total_hits / char.total_ab if char.total_ab > 0 else 0.0

    return {
        "games_played": char.total_games,
        "at_bats": char.total_ab,
        "hits": char.total_hits,
        "homeruns": char.total_homeruns,
        "rbis": char.total_rbis,
        "batting_average": round(avg, 3)
    }
