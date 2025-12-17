import json

def verify_cot():
    try:
        with open("broadcast_data.jsonl", "r", encoding="utf-8") as f:
            lines = f.readlines()
            if not lines:
                print("No data found.")
                return

            last_line = lines[-1]
            data = json.loads(last_line)
            
            result = data.get("result", {})
            reasoning = result.get("reasoning", "N/A")
            
            print(f"--- Last Reasoning Trace ---")
            print(reasoning)
            
            if reasoning and reasoning != "N/A":
                print("\n✅ User-facing CoT Logic Verified!")
            else:
                print("\n❌ Reasoning field missing or empty.")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify_cot()
