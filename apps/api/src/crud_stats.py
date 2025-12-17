from sqlalchemy.orm import Session
from sqlalchemy import select
from .models import PlateAppearance, ResultCode

def get_character_stats(db: Session, character_id: int) -> dict:
    # Get all PAs for this character
    pas = db.execute(select(PlateAppearance).where(PlateAppearance.batter_character_id == character_id)).scalars().all()
    
    games_played = len(set(pa.match_id for pa in pas))
    total_pa = len(pas)
    
    # Simplified logic: Treat all PAs as At Bats for now (unless Walk/Sacrifice logic is added later)
    at_bats = len([pa for pa in pas if pa.result_code != ResultCode.WALK])
    
    hits = len([pa for pa in pas if pa.result_code in [ResultCode.HIT, ResultCode.HOMERUN]])
    homeruns = len([pa for pa in pas if pa.result_code == ResultCode.HOMERUN])
    
    # RBI logic (simplified as per previous implementation)
    rbis = homeruns 
    
    avg = hits / at_bats if at_bats > 0 else 0.0
    
    return {
        "games_played": games_played,
        "at_bats": at_bats,
        "hits": hits,
        "homeruns": homeruns,
        "rbis": rbis,
        "batting_average": round(avg, 3)
    }
