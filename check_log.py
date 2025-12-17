def check_log():
    try:
        with open("simulation_log.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in lines[-20:]: # Last 20 lines
                print(line.strip())
                
        # Check for substitution
        found = any("투수 교체" in line for line in lines)
        if found:
            print("\n✅ SUCCESS: Pitcher Substitution Log Found!")
        else:
            print("\n❌ NOT FOUND: No substitution log yet.")
            
    except Exception as e:
        print(f"Error reading log: {e}")

if __name__ == "__main__":
    check_log()
