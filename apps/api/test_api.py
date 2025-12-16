import os
import sys
from fastapi.testclient import TestClient

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

# Set dummy DATABASE_URL for testing (needed by db.py)
os.environ["DATABASE_URL"] = "sqlite:///./test_api.db"
os.environ["GOOGLE_CLIENT_ID"] = "dummy_client_id"

from src.main import app
from src.db import get_db
from src.models import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Use SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_api.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def test_api_flow():
    # Setup DB
    Base.metadata.create_all(bind=engine)
    
    try:
        # 1. Create World
        response = client.post("/api/v1/worlds", json={"world_name": "API Test World"})
        assert response.status_code == 200
        world_data = response.json()
        world_id = world_data["world_id"]
        print(f"Created World: {world_id}")

        # 2. Create Character
        response = client.post("/api/v1/characters", json={
            "world_id": world_id,
            "nickname": "API Slugger",
            "is_user_created": True
        })
        assert response.status_code == 200
        char_data = response.json()
        char_id = char_data["character_id"]
        print(f"Created Character: {char_id}")

        # 3. Create Teams
        response = client.post("/api/v1/teams", json={
            "world_id": world_id,
            "team_name": "API Tigers",
            "user_character_id": char_id
        })
        assert response.status_code == 200
        team1_data = response.json()
        team1_id = team1_data["team_id"]
        print(f"Created Team 1: {team1_id}")

        response = client.post("/api/v1/teams", json={
            "world_id": world_id,
            "team_name": "API Lions"
        })
        assert response.status_code == 200
        team2_data = response.json()
        team2_id = team2_data["team_id"]
        print(f"Created Team 2: {team2_id}")

        # 4. Create Match
        response = client.post("/api/v1/matches", json={
            "world_id": world_id,
            "home_team_id": team1_id,
            "away_team_id": team2_id
        })
        assert response.status_code == 200
        match_data = response.json()
        match_id = match_data["match_id"]
        print(f"Created Match: {match_id}")

        # 5. Get Match
        response = client.get(f"/api/v1/matches/{match_id}")
        assert response.status_code == 200
        assert response.json()["match_id"] == match_id
        print("Verified Match Retrieval")

        print("API Flow Test Passed Successfully!")

    finally:
        # Cleanup
        if os.path.exists("./test_api.db"):
            os.remove("./test_api.db")

if __name__ == "__main__":
    test_api_flow()
