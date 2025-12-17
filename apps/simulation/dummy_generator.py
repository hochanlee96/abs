import random
from faker import Faker
from uuid import uuid4
from .models import Role, Character, PlayerState, Team, GameState, Half, SimulationStatus

fake = Faker('ko_KR')

def create_random_stats():
    """1~100 사이의 랜덤 능력치 생성 (정규 분포 느낌을 주기 위해 triangular 사용)"""
    return int(random.triangular(30, 100, 60))

def create_dummy_character(role: Role) -> Character:
    # 기본 스탯 (Triangle 분포)
    base_stat = lambda: int(random.triangular(30, 100, 60))
    # 서브 스탯 (균등 or 정규)
    sub_stat = lambda: int(random.randint(30, 90))
    
    # 포지션 할당
    pos_main = "RP" if role == Role.PITCHER else random.choice(["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF"])
    
    return Character(
        character_id=str(uuid4()),
        name=fake.name(),
        role=role,
        contact=base_stat(),
        power=base_stat(),
        speed=base_stat(),
        
        # Extended Stats
        mental=sub_stat(),
        stamina=random.randint(60, 100) if role == Role.PITCHER else random.randint(40, 80),
        recovery=sub_stat(),
        velocity_max=int(random.triangular(130, 160, 144)),
        
        # Pitch Grades
        pitch_fastball=sub_stat(),
        pitch_slider=sub_stat(),
        pitch_curve=sub_stat(),
        pitch_changeup=sub_stat(),
        pitch_splitter=sub_stat(),
        
        # Batter Details
        eye=sub_stat(),
        clutch=sub_stat(),
        contact_left=base_stat(),
        contact_right=base_stat(),
        power_left=base_stat(),
        power_right=base_stat(),
        
        # Defense
        defense_range=sub_stat(),
        defense_error=random.randint(10, 80), # 10(좋음) ~ 80(나쁨) - 해석 나름이나 여기선 수치가 높을수록 실책빈도가 높다는 의미로 가정? 아니면 능력치니까 높을수록 좋은걸로? models.py 설명엔 '포구 실책 빈도'라고 되어있음.
        # models.py: defense_error: int = Field(50, description="포구 실책 빈도 (낮을수록 좋음)")
        # 그렇다면 낮게 생성해야 좋음.
        defense_arm=sub_stat(),
        position_main=pos_main,
        position_sub=None
    )

def create_dummy_player(role: Role) -> PlayerState:
    character = create_dummy_character(role)
    return PlayerState(
        character=character,
        current_stamina=random.randint(80, 100),
        condition=random.choice(["BEST", "GOOD", "NORMAL", "BAD"])
    )

def create_dummy_team(name: str) -> Team:
    # 1. 투수 5명 생성
    pitchers = [create_dummy_player(Role.PITCHER) for _ in range(5)]
    # 2. 타자 9명 생성 (선발 라인업용)
    batters = [create_dummy_player(Role.BATTER) for _ in range(9)]
    # 3. 후보 타자 3명 생성
    bench = [create_dummy_player(Role.BATTER) for _ in range(3)]
    
    return Team(
        team_id=str(uuid4()),
        name=name,
        roster=pitchers + batters + bench
    )

def init_dummy_game(home_name: str = "Home Tigers", away_name: str = "Away Lions") -> GameState:
    home_team = create_dummy_team(home_name)
    away_team = create_dummy_team(away_name)
    
    return GameState(
        match_id=str(uuid4()),
        home_team=home_team,
        away_team=away_team,
        status=SimulationStatus.READY
    )

if __name__ == "__main__":
    # Test Generation
    game = init_dummy_game()
    print(f"Game Initialized: {game.away_team.name} (Away) vs {game.home_team.name} (Home)")
    pitcher = game.get_current_pitcher()
    batter = game.get_current_batter()
    
    print(f"Current Matchup: Pitcher {pitcher.character.name} vs Batter {batter.character.name}")
    print(f"Pitcher Stats (Stuff/Vel/Ctrl): {pitcher.character.pitcher_stats}")
    print(f"Batter Stats (Con/Pow/Spd): {batter.character.batter_stats}")
    
    # Next Batter Check
    next_batter_info = game.get_next_batter_info()
    print(f"Next Batter: {next_batter_info['name']}")
