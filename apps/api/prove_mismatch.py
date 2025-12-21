import json

file_path = "apps/api/match_result_decoded.json"

with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

logs = data.get("logs", [])

found_count = 0
for log in logs:
    batter_name = log.get("current_batter", {}).get("name")
    if batter_name == "Mr_Kimchi":
        desc = log.get("result", {}).get("description", "")
        print(f"--- Log #{found_count+1} ---")
        print(f"Structured Batter Name: '{batter_name}'")
        print(f"Description Text: '{desc}'")
        found_count += 1
        if found_count >= 3: break
