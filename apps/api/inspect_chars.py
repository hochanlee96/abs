from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from src.models import Character

DATABASE_URL = "mysql+pymysql://app:app@mariadb:3306/baseball"
engine = create_engine(DATABASE_URL)

with Session(engine) as session:
    chars = session.execute(select(Character)).scalars().all()
    print(f"Found {len(chars)} characters:")
    for c in chars:
        print(f"ID: {c.character_id}, Name: {c.nickname}, World: {c.world_id}, Owner: {c.owner_account_id}, Created: {c.character_id}") # ID is timestamp-ish
