import asyncio
import json
import os
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

@router.websocket("/ws/simulation/replay/{match_id}")
async def ws_simulation_replay(websocket: WebSocket, match_id: str):
    await websocket.accept()
    
    try:
        await websocket.send_json({"type": "CONNECTED", "match_id": match_id})
        
        # Read the broadcast_data.jsonl file
        file_path = "broadcast_data.jsonl"
        if not os.path.exists(file_path):
            await websocket.send_json({"type": "ERROR", "message": "No simulation data found. Run mock_engine first."})
            await websocket.close()
            return

        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        # Extract rosters
        home_roster = {}
        away_roster = {}
        
        for line in lines:
            if not line.strip(): continue
            d = json.loads(line)
            
            # Extract batter info
            batter = d.get("current_batter")
            if batter:
                if d["half"] == "TOP": # Away team batting
                    away_roster[batter["name"]] = batter
                else: # Home team batting
                    home_roster[batter["name"]] = batter
                    
            # Extract pitcher info (optional, but good for completeness)
            pitcher = d.get("current_pitcher")
            if pitcher:
                if d["half"] == "TOP": # Home team pitching
                    home_roster[pitcher["name"]] = pitcher
                else: # Away team pitching
                    away_roster[pitcher["name"]] = pitcher

        # Send Rosters
        await websocket.send_json({
            "type": "ROSTERS",
            "home": list(home_roster.values()),
            "away": list(away_roster.values())
        })
            
        for line in lines:
            if not line.strip():
                continue
                
            data = json.loads(line)
            
            # Send PA event
            await websocket.send_json({
                "type": "PA",
                "data": data
            })
            
            # Send FINAL if it's the last line (simplified logic)
            # In a real stream, we'd check game status
            
            # Simulate delay for "live" feel
            await asyncio.sleep(1.0) 
            
        await websocket.send_json({"type": "FINAL", "scores": {"home": data["home_score"], "away": data["away_score"]}})
            
    except WebSocketDisconnect:
        print(f"Client disconnected from replay {match_id}")
    except Exception as e:
        print(f"Error in replay: {e}")
        try:
            await websocket.send_json({"type": "ERROR", "message": str(e)})
        except:
            pass
