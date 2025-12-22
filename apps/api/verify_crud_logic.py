
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup paths
sys.path.append(os.getcwd())

try:
    from src.models import Base, Training
    from src import crud_game
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

# In-memory DB
engine = create_engine("sqlite:///:memory:")
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

def test_crud():
    print("Testing CRUD Logic...")
    db = SessionLocal()
    try:
        # 1. Get Trainings (Should be empty)
        trainings = crud_game.get_trainings(db)
        print(f"Trainings: {len(trainings)}")
        
        # 2. Create Training
        t1 = crud_game.create_training(db, "TestTrain", power_delta=1)
        print(f"Created Training: {t1.train_name}, Power: {t1.power_delta}")
        
        # 3. Verify Training
        trainings = crud_game.get_trainings(db)
        print(f"Trainings after create: {len(trainings)}")
        
        # 4. Create Character Test
        print("Testing Create Character...")
        # Create dummy world first
        world = crud_game.create_world(db, "TestWorld")
        
        # Call create_character
        char = crud_game.create_character(
            db, world_id=world.world_id, nickname="TestChar", 
            contact=5, power=5, speed=5
        )
        print(f"Created Character: {char.nickname} (ID: {char.character_id})")
        
        if char.total_hits == 0:
             print("✅ Character Creation Verification Passed!")

    except Exception as e:
        print(f"❌ Exception during CRUD: {e}")
        # import traceback
        # traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_crud()
