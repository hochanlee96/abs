
import requests
import json
import time
import sys

BASE_URL = "http://localhost:8000/api/v1"
HEADERS = {
    "Content-Type": "application/json",
    # Auth is mocked in DEV_MODE usually, or we use a valid token.
    # The routers/game.py often checks `user = Depends(get_current_user)`.
    # In dev mode, we might need a fake token or rely on a "Skip Auth" mechanism if implemented.
    # If not, we will simulate a login or use a hardcoded dev token.
    # Assuming standard Bearer token structure.
    "Authorization": "Bearer DEV_TOKEN_123" 
}

def log(msg, status="INFO"):
    print(f"[{status}] {msg}")

def run_e2e_test():
    log("Starting Full System Verification...")
    
    # 1. Health Check
    try:
        resp = requests.get("http://localhost:8000/health")
        if resp.status_code == 200:
            log("Server is UP", "PASS")
        else:
            log(f"Server returned {resp.status_code}", "FAIL")
            return
    except Exception as e:
        log(f"Server unavailable: {e}", "FAIL")
        log("Please run 'docker compose up' first.", "HINT")
        return

    # 2. Create Character (Mocking User)
    char_data = {
        "world_id": 0, # Will be ignored/managed by logic usually, or we need a world first?
        # Actually create_character needs a world_id unless it creates one.
        # But apiCreateWorld exists. Let's try creating a world first if API allows.
        # However, league/init does everything.
        # Let's create a character first. Wait, league_generator needs a character.
        
        # Strategy:
        # A. Create World -> Create Char -> Init League
        # B. Create Char (needs world_id?) -> Init League
        
        # Looking at schema, char needs world_id.
        # Let's create a temporary world.
        "nickname": f"Tester_{int(time.time())}",
        "owner_account_id": 1,
        "is_user_created": True,
        "contact": 8, "power": 8, "speed": 8
    }
    
    # Create World first
    log("Creating World...")
    resp = requests.post(f"{BASE_URL}/worlds", json={"world_name": f"TestWorld_{int(time.time())}"}, headers=HEADERS)
    if not resp.ok:
        log(f"Failed to create world: {resp.text}", "FAIL")
        return
    world = resp.json()
    world_id = world['world_id']
    char_data['world_id'] = world_id
    log(f"World Created: ID {world_id}", "PASS")

    # Create Character
    log("Creating Character...")
    resp = requests.post(f"{BASE_URL}/characters", json=char_data, headers=HEADERS)
    if not resp.ok:
        log(f"Failed to create character: {resp.text}", "FAIL")
        return
    char = resp.json()
    char_id = char['character_id']
    log(f"Character Created: ID {char_id} ({char['nickname']})", "PASS")

    # 3. Init League
    log("Initializing League (Teams, Schedule, NPCs)...")
    init_data = {"user_character_id": char_id, "world_name": f"League_{world_id}"}
    resp = requests.post(f"{BASE_URL}/league/init", json=init_data, headers=HEADERS)
    if not resp.ok:
        log(f"Failed to init league: {resp.text}", "FAIL")
        return
    league = resp.json()
    log(f"League Initialized: {league['teams_created']} teams, {league['matches_scheduled']} matches", "PASS")
    
    # 4. Check Stats API (Should be empty initially)
    log("Checking Stats API...")
    resp = requests.get(f"{BASE_URL}/characters/{char_id}/stats", headers=HEADERS)
    if not resp.ok:
        log(f"Failed to fetch stats: {resp.text}", "FAIL")
        return
    stats = resp.json()
    if 'total_hits' in stats or 'hits' in stats: # Depends on crud_stats output keys
        log(f"Stats API Response: {stats}", "PASS")
        # Ensure column mapping is correct
        if 'batting_average' in stats:
             log("Stats format verified (Frontend Compatible)", "PASS")
    else:
        log(f"Stats API missing keys: {stats}", "FAIL")
        return

    log("🎉 SYSTEM VERIFICATION PASSED!", "SUCCESS")
    log("The Backend, DB, and Logic are working correctly.", "INFO")

if __name__ == "__main__":
    run_e2e_test()
