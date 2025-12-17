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
        
    # Pre-generate unique names for all NPCs (4 teams * 9 players = 36)
    required_names_count = 4 * 9
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
        # If user is in this team (Team 0), we need 8 NPCs. Else 9.
        current_roster_size = 9
        if i == 0:
            current_roster_size = 8
            # Add User Player
            db.add(TeamPlayer(team_id=team.team_id, character_id=user_char.character_id, role=Role.USER))
        
        for _ in range(current_roster_size):
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
                speed=spd
            )
            
            # Link TeamPlayer
            db.add(TeamPlayer(team_id=team.team_id, character_id=npc.character_id, role=Role.AI))
            
    # Add User to Team 0 explicitly now
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
