from sqlalchemy import create_engine, text
import os

# Use the internal docker DNS name for mariadb
DATABASE_URL = "mysql+pymysql://app:app@mariadb:3306/baseball"
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE matches ADD COLUMN game_state JSON"))
        print("Successfully added game_state column to matches table.")
    except Exception as e:
        print(f"Error executing ALTER TABLE: {e}")
