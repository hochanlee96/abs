import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from apps.simulation.models import GameState, SimulationResult, PlayerState, Role, Character
from apps.simulation.rule_engine import BaseballRuleEngine
from apps.simulation.engine import run_engine
from apps.simulation.dummy_generator import init_dummy_game

def test_loaded_bases_scoring():
    print(">>> Testing Loaded Bases Scoring Logic...")
    
    # 1. Setup Game
    game = init_dummy_game()
    
    # 2. Setup Loaded Bases
    # Dummy Players
    p1 = PlayerState(character=Character(character_id="1", name="Runner1", role=Role.BATTER, contact=50, power=50, speed=50))
    p2 = PlayerState(character=Character(character_id="2", name="Runner2", role=Role.BATTER, contact=50, power=50, speed=50))
    p3 = PlayerState(character=Character(character_id="3", name="Runner3", role=Role.BATTER, contact=50, power=50, speed=50))
    
    game.bases.basec1 = p1
    game.bases.basec2 = p2
    game.bases.basec3 = p3
    
    initial_score = game.away_score # Top Inning
    
    # 3. Simulate 1B (Single)
    res = SimulationResult(
        result_code="1B",
        description="Test Single",
        reasoning="Test"
    )
    
    print(f"Before: Score {game.away_score}, Bases: {[p.character.name if p else 'None' for p in [game.bases.basec1, game.bases.basec2, game.bases.basec3]]}")
    
    runs = BaseballRuleEngine.apply_result(game, res)
    
    print(f"Runs Scored: {runs}")
    print(f"After: Score {game.away_score}, Bases: {[p.character.name if p else 'None' for p in [game.bases.basec1, game.bases.basec2, game.bases.basec3]]}")
    
    # Assertion
    assert runs == 1, f"Expected 1 run, got {runs}"
    assert game.away_score == initial_score + 1, "Score not updated correctly"
    
    # Batter should be on 1st (Assuming logic puts batter on 1st). 
    # Current batter in game might be different from who generated result unless we sync.
    # In apply_result, it calls game.get_current_batter().
    batter = game.get_current_batter()
    assert game.bases.basec1.character.name == batter.character.name, f"Expected 1st base {batter.character.name}, got {game.bases.basec1.character.name}"
    assert game.bases.basec2.character.name == "Runner1"
    assert game.bases.basec3.character.name == "Runner2"
    # Runner3 Scored
    
    print("✅ Loaded Bases Single Test Passed!")

def test_full_simulation_integration():
    print("\n>>> Testing Full Simulation Integration...")
    game = init_dummy_game()
    game.match_id = "test_match_001"
    
    try:
        final_state = run_engine(game)
        print("✅ Simulation successfully ran.")
        print(f"Logs generated: {len(final_state.logs)}")
        if len(final_state.logs) > 0:
            print(f"Last Log: {final_state.logs[-1]}")
    except Exception as e:
        print(f"❌ Simulation Failed: {e}")
        raise e

if __name__ == "__main__":
    test_loaded_bases_scoring()
    # Uncomment to run full sim (might involve LLM costs/time)
    test_full_simulation_integration()
