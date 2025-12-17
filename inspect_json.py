import json

def inspect_last_json():
    try:
        with open("broadcast_data.jsonl", "r", encoding="utf-8") as f:
            lines = f.readlines()
            if not lines:
                print("No data.")
                return
            
            last = lines[-1]
            data = json.loads(last)
            res = data.get("result", {})
            
            print(f"Result Code: {res.get('result_code')}")
            print(f"Final Bases: {res.get('final_bases')}")
            print(f"Reasoning: {res.get('reasoning')}")
            print(f"Runners in State: {data.get('runners')}")
    except Exception as e:
        print(f"Err: {e}")

if __name__ == "__main__":
    inspect_last_json()
