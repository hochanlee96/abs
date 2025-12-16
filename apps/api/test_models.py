import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models import Base, Account, World, Team, Character, TeamPlayer, Match, PlateAppearance, Training, TrainingSession, Role, MatchStatus, InningHalf, ResultCode

# Use SQLite for testing
DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def test_models():
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        print("Creating world...")
        world = World(world_name="Test World")
        db.add(world)
        db.commit()
        db.refresh(world)
        
        print("Creating account...")
        acc = Account(google_sub="12345", email="test@example.com")
        db.add(acc)
        db.commit()
        db.refresh(acc)
        
        print("Creating character...")
        char = Character(world_id=world.world_id, owner_account_id=acc.account_id, nickname="Slugger", is_user_created=True)
        db.add(char)
        db.commit()
        db.refresh(char)
        
        print("Creating team...")
        team = Team(world_id=world.world_id, team_name="Tigers", user_character_id=char.character_id)
        db.add(team)
        db.commit()
        db.refresh(team)
        
        print("Adding player to team...")
        tp = TeamPlayer(team_id=team.team_id, character_id=char.character_id, role=Role.BATTER)
        db.add(tp)
        db.commit()
        
        print("Creating match...")
        team2 = Team(world_id=world.world_id, team_name="Lions")
        db.add(team2)
        db.commit()
        db.refresh(team2)
        
        match = Match(world_id=world.world_id, home_team_id=team.team_id, away_team_id=team2.team_id, status=MatchStatus.SCHEDULED)
        db.add(match)
        db.commit()
        
        print("All models verified successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        db.close()
        # Cleanup
        # if os.path.exists("./test.db"):
        #     os.remove("./test.db")

if __name__ == "__main__":
    test_models()
