import random
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from .. import crud_game
from ..models import MatchStatus, Role, TeamPlayer

TEAM_NAMES = [
    "Seoul Tigers", "Busan Bears", "Incheon Wyverns", "Gwangju Champions",
    "Daegu Lions", "Daejeon Eagles", "Suwon Wiz", "Changwon Dinos"
]

FIRST_NAMES = [
    "Min-soo", "Ji-hoon", "Hyun-woo", "Dong-hyuk", "Joon-ho", "Sang-min", "Sung-hoon", "Kyung-ho",
    "Jun-young", "Min-ji", "Seo-jun", "Ye-jun", "Do-hyun", "Joo-won", "Min-kyu", "Young-ho",
    "Jin-woo", "Tae-min", "Ji-sub", "Hyun-jin", "Seung-gi", "Si-woo", "Ha-joon", "Eun-woo"
]
LAST_NAMES = [
    "Kim", "Lee", "Park", "Choi", "Jung", "Kang", "Cho", "Yoon",
    "Jang", "Lim", "Han", "Oh", "Seo", "Shin", "Kwon", "Hwang",
    "Ahn", "Song", "Jeon", "Hong", "Yoo", "Ko", "Moon", "Yang"
]

def generate_random_name():
    return f"{random.choice(LAST_NAMES)} {random.choice(FIRST_NAMES)}"

def generate_league(db: Session, user_character_id: int, world_name: str = "New League") -> dict:
    # 1. Create World
    world = crud_game.create_world(db, world_name)
    
    # 2. Generate Teams
    selected_teams = random.sample(TEAM_NAMES, 4)
    teams = []
    
    # Assign User to the first team
    user_char = crud_game.get_character(db, user_character_id)
    if not user_char:
        raise ValueError("User character not found")
        
    # Pre-generate unique names for all NPCs (4 teams * 15 players = 60)
    required_names_count = 4 * 15
    unique_names = set()
    while len(unique_names) < required_names_count:
        unique_names.add(generate_random_name())
    
    unique_names_list = list(unique_names)
    name_idx = 0
    
    # 3. Create Teams and Rosters
    for i, name in enumerate(selected_teams):
        team = crud_game.create_team(db, world.world_id, name)
        teams.append(team)
        
        # Determine Roster Size for this team
        # We need at least 9 batters + 5 pitchers = 14 players.
        # Let's target 15 players per team (5 Pitchers, 10 Batters).
        
        current_roster_size = 15
        user_team_npc_count = 14 # 1 User + 14 NPCs = 15 total
        
        if i == 0:
            count = user_team_npc_count
            # Add User Player
            db.add(TeamPlayer(team_id=team.team_id, character_id=user_char.character_id, role=Role.USER))
        else:
            count = current_roster_size
        
        for _ in range(count):
            # Stats
            con = max(1, min(10, int(random.gauss(5, 1.5))))
            pow = max(1, min(10, int(random.gauss(5, 1.5))))
            spd = max(1, min(10, int(random.gauss(5, 1.5))))
            
            # Name
            npc_name = unique_names_list[name_idx]
            name_idx += 1
            
            npc = crud_game.create_character(
                db, 
                world.world_id, 
                npc_name, 
                owner_account_id=None, 
                is_user_created=False,
                contact=con, 
                power=pow, 
                speed=spd,
                # [Phase 2] Random Stats
                mental=random.randint(40, 70),
                recovery=random.randint(40, 80),
                stamina=random.randint(60, 100) if i == 0 else random.randint(30, 80), # 1선발은 체력 높게
                velocity_max=int(random.gauss(140, 5)),
                pitch_fastball=int(random.gauss(50, 10)),
                pitch_slider=int(random.gauss(40, 10)),
                pitch_curve=int(random.gauss(40, 10)),
                pitch_changeup=int(random.gauss(40, 10)),
                pitch_splitter=int(random.gauss(30, 10)),
                eye=int(random.gauss(50, 10)),
                clutch=int(random.gauss(50, 10)),
                contact_left=int(random.gauss(con*10, 10)), # 기본값 * 10 스케일
                contact_right=int(random.gauss(con*10, 10)),
                power_left=int(random.gauss(pow*10, 10)),
                power_right=int(random.gauss(pow*10, 10)),
                defense_range=int(random.gauss(50, 15)),
                defense_error=int(random.gauss(50, 15)),
                defense_arm=int(random.gauss(50, 15)),
                position_main="PITCHER" if _ < 5 else "DH" # 0~4번 인덱스(5명)는 투수, 나머지는 야수(DH/Fielder)
            )
            
            # User Character Position Fix
            if i == 0 and _ == 0:
                 # This logic block creates NPCs, but waiting... 
                 # Ah, user is added SEPARATELY below or above?
                 # Looking at line 59: db.add(TeamPlayer(..., role=Role.USER))
                 # But the user character entity itself might have random position if not set properly?
                 # No, user character is passed in via `user_character_id`. We need to UPDATE it.
                 pass
            
            # Link TeamPlayer
            # Link TeamPlayer
            # All NPCs have Role.AI
            role = Role.AI
            db.add(TeamPlayer(team_id=team.team_id, character_id=npc.character_id, role=role))
            
    # Add User to Team 0 explictly now
    # Force User Position to Batter if not valid
    if "P" in user_char.position_main.upper() or "PITCHER" in user_char.position_main.upper():
        user_char.position_main = "DH" # 강제 타자 전환
    
    # Also update user character's world_id to the new world
    user_char.world_id = world.world_id
    db.add(user_char)
    
    db.commit()
    
    # 4. Generate Schedule (Round Robin)
    t_ids = [t.team_id for t in teams]
    match_interval = timedelta(hours=3)
    start_time = datetime.utcnow() + timedelta(minutes=10)
    
    # Simple Round Robin for 4 teams
    pairings = [
        [(0,1), (2,3)],
        [(0,2), (1,3)],
        [(0,3), (1,2)]
    ]
    
    matches_created = []
    current_time = start_time
    
    for r, round_pairs in enumerate(pairings):
        for (i1, i2) in round_pairs:
            home_idx, away_idx = (i1, i2) if random.random() > 0.5 else (i2, i1)
            home_team_id = t_ids[home_idx]
            away_team_id = t_ids[away_idx]
            
            match = crud_game.create_match(db, world.world_id, home_team_id, away_team_id)
            match.scheduled_at = current_time
            # Init game_state as empty dict to signal readiness or keep null until start
            match.game_state = {} 
            matches_created.append(match)
        current_time += match_interval
        
    db.commit()
    
    return {
        "world_id": world.world_id,
        "user_team_id": teams[0].team_id,
        "teams_created": len(teams),
        "matches_scheduled": len(matches_created)
    }
