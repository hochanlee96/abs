from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from src.models import Character
from src import crud_game

DATABASE_URL = "mysql+pymysql://app:app@mariadb:3306/baseball"
engine = create_engine(DATABASE_URL)

def debug_delete(char_id):
    with Session(engine) as db:
        print(f"Attempting to delete character {char_id}...")
        try:
            success = crud_game.delete_character(db, char_id)
            if success:
                print("Deletion SUCCESS")
            else:
                print("Deletion FAILED (returned False)")
        except Exception as e:
            print(f"Deletion ERROR: {e}")

if __name__ == "__main__":
    # Try deleting the most recent character found in previous step (ID 114)
    debug_delete(114)
