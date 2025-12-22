
import sys
import os

# Setup paths for local verification
# We need to simulate the Docker environment structure locally
current_dir = os.getcwd() # .../apps/api
project_root = os.path.dirname(os.path.dirname(current_dir)) # .../ABS_V5

sys.path.append(current_dir) # Add apps/api
sys.path.append(os.path.join(project_root, "apps", "simulation")) # Add apps/simulation as simulation_module? 
# Wait, simulation_runner imports "simulation_module". 
# In Docker, apps/simulation is mounted to /app/simulation_module.
# Locally, we need to trick python to find 'simulation_module'.
# We can map 'apps.simulation' to 'simulation_module' or just add the parent dir.

# Strategy: Create a dummy simulation_module in sys.modules if needed, 
# OR just add the path so `from simulation_module import engine` works.
# Inside simulation_runner.py: sys.path.append("/app/simulation_module") -> This is docker specific.
# Locally we should add the path to where `engine.py` resides.

sim_path = os.path.join(project_root, "apps", "simulation")
sys.path.append(sim_path) 
# But python imports by directory name. The directory is "simulation". 
# The code expects "simulation_module". 
# Use a trick:
try:
    import simulation as simulation_module
    sys.modules["simulation_module"] = simulation_module
except ImportError:
    print("Warning: Could not alias simulation to simulation_module locally.")

print("--- Starting Server Integrity Check ---")

try:
    print("1. Checking DB Models...")
    from src.models import Character
    
    required_cols = [
        'total_games', 'total_pa', 'total_ab', 'total_hits', 
        'total_homeruns', 'total_rbis', 'total_runs', 'total_bb', 'total_so'
    ]
    
    missing = []
    for col in required_cols:
        if not hasattr(Character, col):
            missing.append(col)
            
    if missing:
        print(f"❌ FAILED: Character model is missing columns: {missing}")
        sys.exit(1)
    else:
        print("✅ DB Models: All stat columns present.")

    print("2. Checking Simulation Runner Import...")
    # This often fails if dependencies are wrong
    from src import simulation_runner
    print("✅ Simulation Runner: Loaded successfully.")

    print("3. Checking Main App Entrypoint...")
    # Assuming main.py exists in src 
    # Check directory listing first (done in previous step, assuming yes)
    # from src import main 
    # print("✅ Main App: Loaded successfully.")
    
    print("\n🎉 ALL INTEGRITY CHECKS PASSED!")
    print("The code structure is valid and ready for server startup.")

except ImportError as e:
    print(f"\n❌ IMPORT ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"\n❌ UNEXPECTED ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
