import requests
import sys

BASE_URL = "http://localhost:8000/api/v1"

def test_create():
    # 1. Create World
    print("Creating World...")
    r = requests.post(f"{BASE_URL}/worlds", json={"world_name": "Test World"})
    if r.status_code != 200:
        print(f"Failed to create world: {r.text}")
        return
    world = r.json()
    world_id = world["world_id"]
    print(f"World Created: {world_id}")

    # 2. Create Character
    print("Creating Character...")
    payload = {
        "world_id": world_id,
        "nickname": "Test Slugger",
        "is_user_created": True
        # owner_account_id is optional, skipping for now
    }
    r = requests.post(f"{BASE_URL}/characters", json=payload)
    if r.status_code != 200:
        print(f"Failed to create character: {r.text}")
        return
    char = r.json()
    print(f"Character Created: {char}")
    print("SUCCESS")

if __name__ == "__main__":
    try:
        test_create()
    except Exception as e:
        print(f"Error: {e}")
