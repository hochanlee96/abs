import pymysql
import json
import re

# DB Config
DB_CONFIG = {
    "host": "localhost",
    "port": 3307,
    "user": "app",
    "password": "app",
    "database": "baseball",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": True
}

def backfill():
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cursor:
            # 1. Schema Patch: Add columns if missing (to avoid DB reset)
            print("Checking schema...")
            try:
                cursor.execute("SELECT runs_scored FROM plate_appearances LIMIT 1")
            except Exception:
                print("Adding missing columns (runs_scored, rbi, outs_added)...")
                cursor.execute("ALTER TABLE plate_appearances ADD COLUMN runs_scored INT DEFAULT 0")
                cursor.execute("ALTER TABLE plate_appearances ADD COLUMN rbi INT DEFAULT 0")
                cursor.execute("ALTER TABLE plate_appearances ADD COLUMN outs_added INT DEFAULT 0")
            
            # 2. Fetch Matches with logs
            cursor.execute("SELECT match_id, game_state FROM matches WHERE game_state IS NOT NULL")
            matches = cursor.fetchall()
            
            print(f"Found {len(matches)} matches to process.")
            
            for m in matches:
                mid = m['match_id']
                try:
                    gs = m['game_state']
                    if isinstance(gs, str):
                        gs = json.loads(gs)
                    
                    logs = gs.get('logs', [])
                    print(f"Match {mid}: Processing {len(logs)} logs...")
                    
                    # Clean existing PAs for this match to avoid dupes
                    cursor.execute("DELETE FROM plate_appearances WHERE match_id = %s", (mid,))
                    
                    seq = 0
                    current_inning = 1
                    current_half = "TOP"
                    
                    for log in logs:
                        # Extract basic info directly from log structure
                        current_inning = log.get('inning', current_inning)
                        half_str = log.get('half', 'TOP')
                        current_half = "TOP" if half_str == "TOP" else "BOTTOM"
                        
                        # Batter
                        curr_batter = log.get('current_batter', {})
                        batter_name = curr_batter.get('name')
                        
                        # Debug
                        # print(f"Processing batter: {batter_name}")

                        if not batter_name:
                            # Try to parse from description as fallback? No, let's rely on structured first.
                            continue

                        # Result
                        res_obj = log.get('result', {})
                        rc = res_obj.get('result_code', 'GO')
                        runs = res_obj.get('runs_scored', 0)
                        
                        # Find Character ID
                        cursor.execute("SELECT character_id FROM characters WHERE nickname = %s LIMIT 1", (batter_name,))
                        res = cursor.fetchone()
                        if not res:
                            print(f"  -> Unknown batter (skipped): {batter_name}")
                            continue
                            
                        char_id = res['character_id']
                        # print(f"  -> Found ID: {char_id}")
                        
                        # Calc RBI/Outs mapping
                        outs = 0
                        # Check result code for Out types
                        if rc in ['SO', 'FO', 'GO', 'OUT', 'STRIKEOUT', 'FLY_OUT', 'GROUND_OUT']:
                            outs = 1
                            
                        # Normalize RC to Enum (1B, 2B, 3B, HOMERUN, SO, BB, HBP, FO, GO)
                        if rc == "SINGLE": rc = "1B"
                        if rc == "DOUBLE": rc = "2B"
                        if rc == "TRIPLE": rc = "3B"
                        if rc == "HR": rc = "HOMERUN"
                        if rc == "WALK": rc = "BB"
                        if rc == "STRIKEOUT": rc = "SO"
                        if rc == "OUT": rc = "GO" # Generic out fallback
                        
                        rbi = runs
                        
                        seq += 1
                        
                        sql = """
                            INSERT INTO plate_appearances 
                            (match_id, inning, half, seq, batter_character_id, result_code, runs_scored, rbi, outs_added)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        cursor.execute(sql, (mid, current_inning, current_half, seq, char_id, rc, runs, rbi, outs))
                        
                    print(f"Match {mid}: Backfilled {seq} records.")

                except Exception as e:
                    print(f"Error processing match {mid}: {e}")

    finally:
        conn.close()

if __name__ == "__main__":
    backfill()
