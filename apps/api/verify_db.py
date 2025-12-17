from sqlalchemy import create_engine, inspect

DATABASE_URL = "mysql+pymysql://app:app@mariadb:3306/baseball"
engine = create_engine(DATABASE_URL)

inspector = inspect(engine)
columns = [col['name'] for col in inspector.get_columns('matches')]

if 'game_state' in columns:
    print("VERIFIED: game_state column exists.")
else:
    print("FAILED: game_state column missing.")
