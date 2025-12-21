import pymysql
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from apps.api.src import models
from apps.api.src import crud_stats

# Setup DB connection
DATABASE_URL = "mysql+pymysql://app:app@localhost:3307/baseball"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

try:
    # Character ID 1 is Mr_Kimchi (verified)
    char_id = 1
    stats = crud_stats.get_character_stats(db, char_id)
    print(f"Stats for Character {char_id}: {stats}")
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
