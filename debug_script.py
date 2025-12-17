from apps.simulation.dummy_generator import init_dummy_game
from apps.simulation.models import Role

def test_defense_logic():
    print("--- Debug Start ---")
    game = init_dummy_game()
    defense_team = game.away_team # Away team defense first (Home offense)
    
    print(f"Defense Team: {defense_team.name}")
    
    defense_info_lines = []
    for p in defense_team.roster:
        # print(f"Checking {p.character.name} ({p.character.role})")
        if p.character.role == Role.BATTER:
            try:
                # This is the line suspected to cause error
                stats = p.character.batter_stats
                if stats is None:
                    print(f"Stats is None for {p.character.name}")
                    continue
                    
                if "defense" not in stats:
                     print(f"Key 'defense' not found in stats for {p.character.name}: {stats.keys()}")
                     continue
                     
                d_stats = stats["defense"]
                info = f"- {p.character.position_main} {p.character.name}: 범위 {d_stats['range']}, 실책 {d_stats['error']}, 어깨 {d_stats['arm']}"
                defense_info_lines.append(info)
            except Exception as e:
                print(f"Error processing {p.character.name}: {e}")
                
    defense_lineup_str = "\n".join(defense_info_lines)
    print("--- Generated Defense Info ---")
    print(defense_lineup_str)
    print("--- Debug End ---")

if __name__ == "__main__":
    test_defense_logic()
