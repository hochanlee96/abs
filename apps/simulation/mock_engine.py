import json
import time
import random
from uuid import uuid4
from .models import (
    BroadcastData, SimulationResult, Role, Half, 
    Character, PlayerState, Team, GameState, SimulationStatus
)
from .dummy_generator import init_dummy_game

def run_mock_simulation():
    print("--- Mock Simulation Engine Start ---")
    
    # Clear Logs
    with open("broadcast_data.jsonl", "w", encoding="utf-8") as f:
        pass

    game = init_dummy_game()
    
    # Simulate 9 innings
    for inning in range(1, 10):
        for half in [Half.TOP, Half.BOTTOM]:
            game.inning = inning
            game.half = half
            game.outs = 0
            game.bases.basec1 = None
            game.bases.basec2 = None
            game.bases.basec3 = None
            
            print(f"Simulating {inning} {half}...")
            
            while game.outs < 3:
                pitcher = game.get_current_pitcher()
                batter = game.get_current_batter()
                
                # Random Result
                outcomes = ["1B", "2B", "3B", "HR", "OUT", "SO", "BB"]
                weights = [15, 5, 1, 3, 40, 25, 11]
                result_code = random.choices(outcomes, weights=weights)[0]
                
                runs = 0
                desc = ""
                final_bases = [None, None, None] # Simplified base logic for mock
                
                if result_code == "HR":
                    runs = 1
                    desc = f"{batter.character.name} hits a HOMERUN!"
                elif result_code in ["OUT", "SO"]:
                    game.outs += 1
                    desc = f"{batter.character.name} is OUT."
                else:
                    desc = f"{batter.character.name} hits a {result_code}."
                    # Simplified: batter goes to 1st, others advance (not implemented fully in mock)
                    final_bases[0] = batter.character.name
                
                if half == Half.TOP:
                    game.away_score += runs
                else:
                    game.home_score += runs
                
                # Create SimulationResult (The core contract)
                sim_result = SimulationResult(
                    result_code=result_code,
                    description=desc,
                    runners_advanced=False,
                    final_bases=final_bases,
                    runs_scored=runs,
                    pitch_desc="Fastball",
                    hit_desc="Swing"
                )
                
                # Create BroadcastData
                runners_data = [None, None, None] # Simplified
                
                broadcast_data = BroadcastData(
                    match_id=game.match_id,
                    inning=game.inning,
                    half="TOP" if game.half == Half.TOP else "BOTTOM",
                    outs=game.outs,
                    home_score=game.home_score,
                    away_score=game.away_score,
                    current_batter={
                        "name": batter.character.name,
                        "role": "BATTER",
                        "stats": batter.character.batter_stats
                    },
                    current_pitcher={
                        "name": pitcher.character.name,
                        "role": "PITCHER",
                        "stats": pitcher.character.pitcher_stats
                    },
                    runners=runners_data,
                    result=sim_result,
                    next_batter={"name": "Next Batter", "role": "BATTER", "stats": {}}
                )
                
                # Write to file
                with open("broadcast_data.jsonl", "a", encoding="utf-8") as f:
                    f.write(json.dumps(broadcast_data.model_dump(), ensure_ascii=False) + "\n")
                
                game.next_batter()
                # time.sleep(0.1) # Fast generation

    print("--- Mock Simulation Finished ---")

if __name__ == "__main__":
    run_mock_simulation()
