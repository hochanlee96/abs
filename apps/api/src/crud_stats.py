from sqlalchemy.orm import Session
from sqlalchemy import func
from .models import Character, PlateAppearance

def calculate_stats_from_logs(db: Session, character_id: int) -> dict:
    """
    Calculates stats dynamically from PlateAppearance logs.
    """
    # 1. Games Played (Distinct Matches)
    games_played = db.query(func.count(func.distinct(PlateAppearance.match_id)))\
        .filter(PlateAppearance.batter_character_id == character_id)\
        .scalar() or 0
        
    # 2. At Bats (Exclude BB, HBP, SF, SAC)
    at_bats = db.query(func.count(PlateAppearance.pa_id))\
        .filter(PlateAppearance.batter_character_id == character_id)\
        .filter(PlateAppearance.result_code.notin_(["BB", "HBP", "SF", "SAC"]))\
        .scalar() or 0

    # 3. Hits (1B, 2B, 3B, HOMERUN)
    hits = db.query(func.count(PlateAppearance.pa_id))\
        .filter(PlateAppearance.batter_character_id == character_id)\
        .filter(PlateAppearance.result_code.in_(["1B", "2B", "3B", "HOMERUN"]))\
        .scalar() or 0
        
    # 4. Homeruns
    homeruns = db.query(func.count(PlateAppearance.pa_id))\
        .filter(PlateAppearance.batter_character_id == character_id)\
        .filter(PlateAppearance.result_code == "HOMERUN")\
        .scalar() or 0

    # 5. RBI (Sum)
    rbis = db.query(func.sum(PlateAppearance.rbi))\
        .filter(PlateAppearance.batter_character_id == character_id)\
        .scalar() or 0
        
    # 6. Batting Average
    avg = (hits / at_bats) if at_bats > 0 else 0.0
    
    return {
        "games_played": games_played,
        "at_bats": at_bats,
        "hits": hits,
        "homeruns": homeruns,
        "rbis": int(rbis if rbis else 0),
        "batting_average": round(avg, 3)
    }

def get_character_stats(db: Session, character_id: int) -> dict:
    # Use dynamic calculation to reflect backfilled data
    return calculate_stats_from_logs(db, character_id)
