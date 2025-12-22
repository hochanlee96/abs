
import sys
import os
import json
from collections import Counter

# Set path to import from apps
current_dir = os.getcwd()
sys.path.append(current_dir)
print(f"Current Directory: {current_dir}")
print(f"Sys Path: {sys.path}")

try:
    from apps.simulation.engine import resolver_node, SimState
    from apps.simulation.models import (
        GameState, Team, Character, Role, SimulationStatus, 
        DirectorContext, ManagerDecision, PitcherDecision, BatterDecision,
        PitchType, PitchLocation, BattingStyle, TeamStrategy
    )
    from apps.simulation.models import PlayerState
except ImportError as e:
    import traceback
    with open("test_error_log.txt", "w", encoding="utf-8") as f:
        f.write(traceback.format_exc())
        f.write(f"\nImport Error Details: {e}")
    sys.exit(1)

def create_mock_state():
    """Create a realistic mock state for testing"""
    
    # Mock Character
    pitcher_char = Character(
        character_id="p1", name="Pitcher Kim", role=Role.PITCHER,
        contact=50, power=60, speed=50,
        pitch_fastball=60, pitch_slider=50, pitch_curve=50
    )
    batter_char = Character(
        character_id="b1", name="Batter Lee", role=Role.BATTER,
        contact=60, power=70, speed=60, # Good hitter
        eye=60, clutch=60
    )
    
    # Mock Team & Roster
    # We need mock PlayerStates
    from apps.simulation.models import PlayerState
    p_state = PlayerState(character=pitcher_char)
    b_state = PlayerState(character=batter_char)
    
    team_home = Team(team_id="t1", name="Home Team", roster=[p_state, b_state])
    team_away = Team(team_id="t2", name="Away Team", roster=[p_state, b_state])
    
    # Mock Game
    game = GameState(
        match_id="test_match",
        home_team=team_home,
        away_team=team_away,
        inning=1,
        outs=0
    )
    # Inject current pitcher/batter context manually if needed, 
    # but engine uses get_current_pitcher methods which rely on half/roster.
    # Let's assume Top of 1st, Away Batter vs Home Pitcher.
    
    # SimState
    state = SimState(
        game=game,
        director_ctx=DirectorContext(),
        home_manager_decision=ManagerDecision(description="Normal", offense_strategy=TeamStrategy.NORMAL, defense_strategy=TeamStrategy.NORMAL),
        away_manager_decision=ManagerDecision(description="Normal", offense_strategy=TeamStrategy.NORMAL, defense_strategy=TeamStrategy.NORMAL),
        pitcher_decision=PitcherDecision(
            pitch_type=PitchType.FASTBALL, 
            location=PitchLocation.MIDDLE, 
            description="Trying to strike out",
            effort="Full_Power"
        ),
        batter_decision=BatterDecision(
            style=BattingStyle.AGGRESSIVE, 
            aim_pitch_type=PitchType.FASTBALL, # Correct Guess!
            description="Aggressive swing on fastball"
        ),
        last_result=None,
        validator_result=None,
        retry_count=0,
        db_session=None
    )
    
    return state

def run_test(iterations=20):
    print(f"--- Starting Diversity Test ({iterations} iterations) ---")
    results = []
    
    mock_state = create_mock_state()
    
    for i in range(iterations):
        print(f"Running iteration {i+1}...", end="\r")
        try:
            output = resolver_node(mock_state)
            res = output["last_result"]
            results.append(res)
        except Exception as e:
            print(f"\nError in iteration {i+1}: {e}")
            
    print("\n\n--- Test Completed ---")
    
    # Analysis
    codes = [r.result_code for r in results]
    counts = Counter(codes)
    
    print("\n[Result Statistics]")
    total = len(results)
    outs = 0
    hits = 0
    
    for code, count in counts.items():
        percentage = (count / total) * 100
        print(f"- {code}: {count} ({percentage:.1f}%)")
        
        if code in ["GO", "FO", "SO", "LO", "PO", "E", "OUT"]:
            outs += count
        elif code in ["1B", "2B", "3B", "HR"]:
            hits += count
            
    print(f"\nTotal Outs: {outs} ({(outs/total)*100:.1f}%)")
    print(f"Total Hits: {hits} ({(hits/total)*100:.1f}%)")
    
    print("\n[Sample Descriptions]")
    for i, res in enumerate(results[:5]):
        print(f"{i+1}. [{res.result_code}] {res.description}")
        
    # Validation Check
    if outs / total >= 0.5: # At least 50% outs (Target 70% but allow variance in small sample)
        print("\n✅ Balance Check Passed: Out rate is reasonable.")
    else:
        print("\n⚠️ Balance Check Warning: Hit rate causes high scores.")
        
    diverse_codes = len(counts.keys())
    if diverse_codes >= 3:
         print(f"✅ Diversity Check Passed: {diverse_codes} different outcomes.")
    else:
         print(f"⚠️ Diversity Check Warning: Only {diverse_codes} outcome types.")

if __name__ == "__main__":
    run_test(20)
