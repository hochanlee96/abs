import pymysql

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

def sync_stats():
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cursor:
            print("Fetching all characters...")
            cursor.execute("SELECT character_id, nickname FROM characters")
            chars = cursor.fetchall()
            
            for char in chars:
                cid = char['character_id']
                name = char['nickname']
                
                # Calculate Stats from PlateAppearance
                # At Bats (Exclude BB, HBP, SF, SAC)
                sql_ab = """
                    SELECT COUNT(*) as val FROM plate_appearances 
                    WHERE batter_character_id = %s 
                    AND result_code NOT IN ('BB', 'HBP', 'SF', 'SAC')
                """
                cursor.execute(sql_ab, (cid,))
                at_bats = cursor.fetchone()['val']

                # Hits (1B, 2B, 3B, HOMERUN)
                sql_hits = """
                    SELECT COUNT(*) as val FROM plate_appearances 
                    WHERE batter_character_id = %s 
                    AND result_code IN ('1B', '2B', '3B', 'HOMERUN')
                """
                cursor.execute(sql_hits, (cid,))
                hits = cursor.fetchone()['val']

                # Homeruns
                sql_hr = """
                    SELECT COUNT(*) as val FROM plate_appearances 
                    WHERE batter_character_id = %s 
                    AND result_code = 'HOMERUN'
                """
                cursor.execute(sql_hr, (cid,))
                homeruns = cursor.fetchone()['val']

                # RBI
                sql_rbi = """
                    SELECT SUM(rbi) as val FROM plate_appearances 
                    WHERE batter_character_id = %s
                """
                cursor.execute(sql_rbi, (cid,))
                rbi = cursor.fetchone()['val'] or 0

                # Games Played
                sql_gp = """
                    SELECT COUNT(DISTINCT match_id) as val FROM plate_appearances 
                    WHERE batter_character_id = %s
                """
                cursor.execute(sql_gp, (cid,))
                games_played = cursor.fetchone()['val']
                
                # Runs
                sql_runs = """
                    SELECT SUM(runs_scored) as val FROM plate_appearances 
                    WHERE batter_character_id = %s
                """
                cursor.execute(sql_runs, (cid,))
                runs = cursor.fetchone()['val'] or 0
                
                # Walks
                sql_bb = """
                    SELECT COUNT(*) as val FROM plate_appearances 
                    WHERE batter_character_id = %s 
                    AND result_code IN ('BB', 'HBP')
                """
                cursor.execute(sql_bb, (cid,))
                walks = cursor.fetchone()['val']
                
                # Strikeouts
                sql_so = """
                    SELECT COUNT(*) as val FROM plate_appearances 
                    WHERE batter_character_id = %s 
                    AND result_code = 'SO'
                """
                cursor.execute(sql_so, (cid,))
                strikeouts = cursor.fetchone()['val']

                # Update Character Table
                if games_played > 0:
                    update_sql = """
                        UPDATE characters 
                        SET games_played=%s, at_bats=%s, hits=%s, homeruns=%s, rbis=%s, runs=%s, walks=%s, strikeouts=%s
                        WHERE character_id=%s
                    """
                    cursor.execute(update_sql, (games_played, at_bats, hits, homeruns, rbi, runs, walks, strikeouts, cid))
                    print(f"Updated {name}: {hits}/{at_bats} ({games_played} games)")
                else:
                    # Optional: reset to 0 if we want to be strict
                    pass

    finally:
        conn.close()

if __name__ == "__main__":
    sync_stats()
