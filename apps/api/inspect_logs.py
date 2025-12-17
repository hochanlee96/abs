from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from src.models import Match

DATABASE_URL = "mysql+pymysql://app:app@mariadb:3306/baseball"
engine = create_engine(DATABASE_URL)

with Session(engine) as db:
    # Get the most recent match with logs
    match = db.execute(select(Match).where(Match.game_state.is_not(None)).order_by(Match.match_id.desc()).limit(1)).scalar_one_or_none()
    
    if match and match.game_state and 'logs' in match.game_state:
        logs = match.game_state['logs']
        print(f"Found {len(logs)} logs in Match {match.match_id}")
        if len(logs) > 0:
            import json
            print("Sample Log Entry:")
            print(json.dumps(logs[0], indent=2))
    else:
        print("No matches with logs found.")
