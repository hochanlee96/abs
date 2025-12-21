import json

file_path = "apps/api/match_result_decoded.json"

try:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    logs = data.get("logs", [])
    print(f"Total Logs: {len(logs)}")

    kimchi_logs = []
    for log in logs:
        batter = log.get("current_batter", {}).get("name")
        if batter == "Mr_Kimchi":
            desc = log.get("result", {}).get("description", "(No Description)")
            rc = log.get("result", {}).get("result_code", "??")
            kimchi_logs.append(f"[{rc}] {desc}")

    output_file = "apps/api/kimchi_logs_utf8.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"Found {len(kimchi_logs)} logs for Mr_Kimchi:\n")
        for i, msg in enumerate(kimchi_logs, 1):
            f.write(f"{i}. {msg}\n")
    print("Done")

except Exception as e:
    print(f"Error: {e}")
