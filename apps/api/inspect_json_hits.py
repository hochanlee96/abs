import pymysql
import json

DB_CONFIG = {
    "host": "localhost",
    "port": 3307,
    "user": "app",
    "password": "app",
    "database": "baseball",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}

def inspect():
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cursor:
            # 1. Get Match IDs for Mr_Kimchi (ID 1)
            cursor.execute("SELECT DISTINCT match_id FROM plate_appearances WHERE batter_character_id = 1")
            matches = [r['match_id'] for r in cursor.fetchall()]
            
            print(f"Mr_Kimchi played in matches: {matches}")
            
            # 2. Inspect JSON logs for these matches
            for mid in matches:
                cursor.execute("SELECT game_state FROM matches WHERE match_id = %s", (mid,))
                row = cursor.fetchone()
                if not row or not row['game_state']:
                    print(f"Match {mid}: No JSON data")
                    continue
                    
                gs = row['game_state']
                if isinstance(gs, str):
                    gs = json.loads(gs)
                    
                logs = gs.get('logs', [])
                print(f"--- Match {mid} Logs for Mr_Kimchi ---")
                
                count_hits = 0
                count_pa = 0
                
                for log in logs:
                    batter = log.get('current_batter', {}).get('name')
                    # check old format just in case
                    if not batter: batter = log.get('batter', {}).get('name')
                    
                    if batter == "Mr_Kimchi":
                        res = log.get('result', {})
                        rc = res.get('result_code')
                        desc = res.get('description', '')
                        
                        count_pa += 1
                        is_hit = rc in ['1B', '2B', '3B', 'HOMERUN', 'SINGLE', 'DOUBLE', 'TRIPLE', 'HR']
                        if is_hit: count_hits += 1
                        
                        print(f"  PA {count_pa}: {rc} | {desc[:50]}...")
                
                print(f"  => JSON Count: {count_hits} Hits / {count_pa} PAs")
                    
    finally:
        conn.close()

if __name__ == "__main__":
    inspect()
