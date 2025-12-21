import json
import pymysql

# DB Config (Localhost port mapping from docker-compose is 3307)
DB_CONFIG = {
    "host": "localhost",
    "port": 3307,
    "user": "app",
    "password": "app",
    "database": "baseball",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}

output_path = "apps/api/match_result_decoded.json"

try:
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cursor:
            # Matches table has 'game_state' as JSON column.
            # PyMySQL might return it as string or dict depending on version.
            sql = "SELECT game_state FROM matches WHERE LENGTH(game_state) > 100 ORDER BY match_id DESC LIMIT 1"
            cursor.execute(sql)
            result = cursor.fetchone()
            
            if result:
                game_state = result['game_state']
                # If it's already a dict (json type), dump it directly.
                # If it's a string, parse it first.
                if isinstance(game_state, str):
                    data = json.loads(game_state)
                else:
                    data = game_state
                    
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"Successfully saved clean JSON to {output_path}")
            else:
                print("No match found with logs > 100 bytes")
                
    finally:
        conn.close()

except Exception as e:
    print(f"DB Error: {e}")
