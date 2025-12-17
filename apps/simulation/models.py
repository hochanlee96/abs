from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class Role(str, Enum):
    PITCHER = "PITCHER"
    BATTER = "BATTER"

class Half(str, Enum):
    TOP = "TOP"      # 초
    BOTTOM = "BOTTOM" # 말

class SimulationStatus(str, Enum):
    READY = "READY"
    PLAYING = "PLAYING"
    FINISHED = "FINISHED"

# --- Advanced Enums (For Multi-Agent) ---

class Weather(str, Enum):
    SUNNY = "SUNNY" # 맑음
    CLOUDY = "CLOUDY" # 흐림
    RAINY = "RAINY" # 비
    WINDY = "WINDY" # 바람

class UmpireZone(str, Enum):
    NORMAL = "NORMAL"   # 보통
    WIDE = "WIDE"       # 넓음 (투수 유리)
    NARROW = "NARROW"   # 좁음 (타자 유리)
    ERRATIC = "ERRATIC" # 오락가락

class PitchType(str, Enum):
    FASTBALL = "FASTBALL" # 직구
    SLIDER = "SLIDER"     # 슬라이더
    CURVE = "CURVE"       # 커브
    CHANGEUP = "CHANGEUP" # 체인지업
    SPLITTER = "SPLITTER" # 스플리터

class PitchLocation(str, Enum):
    HIGH = "HIGH"
    LOW = "LOW"
    INSIDE = "INSIDE"
    OUTSIDE = "OUTSIDE"
    MIDDLE = "MIDDLE" # 실투 가능성

class BattingStyle(str, Enum):
    AGGRESSIVE = "AGGRESSIVE" # 적극 타격 (초구 공략 등)
    CAUTIOUS = "CAUTIOUS"     # 신중 타격 (공을 많이 봄)
    PULL = "PULL"             # 당겨치기
    PUSH = "PUSH"             # 밀어치기

class TeamStrategy(str, Enum):
    NORMAL = "NORMAL"           # 정상
    BUNT = "BUNT"               # 번트 시도
    HIT_AND_RUN = "HIT_AND_RUN" # 히트 앤드 런
    INFIELD_IN = "INFIELD_IN"   # 전진 수비
    LONG_BALL = "LONG_BALL"     # 장타 노림 (큰거 한방)

# --- Decision Models (Thinking Agents) ---

class DirectorContext(BaseModel):
    """경기 환경 및 총괄 관리"""
    weather: Weather = Weather.SUNNY
    wind_direction: str = "None" # 예: "Center to Home"
    umpire_zone: UmpireZone = UmpireZone.NORMAL

class ManagerDecision(BaseModel):
    """감독의 작전 지시"""
    offense_strategy: TeamStrategy = TeamStrategy.NORMAL # 공격 작전
    defense_strategy: TeamStrategy = TeamStrategy.NORMAL # 수비 작전
    description: str = Field(..., description="작전 지시 이유 (LLM 생각)")

class PitcherDecision(BaseModel):
    """투수의 투구 의도"""
    pitch_type: PitchType
    location: PitchLocation
    effort: str = "Normal" # Normal, Full_Power, Finesse
    description: str = Field(..., description="투구 선택 이유 (LLM 생각)")

class BatterDecision(BaseModel):
    """타자의 타격 의도"""
    aim_pitch_type: Optional[PitchType] = None # 노리는 구종
    aim_location: Optional[PitchLocation] = None # 노리는 코스
    style: BattingStyle
    description: str = Field(..., description="타격 전략 이유 (LLM 생각)")


# --- Base Models (Mapped to DB Schema) ---

class Character(BaseModel):
    character_id: str
    name: str
    role: Role
    # Ability Stats
    contact: int = Field(..., description="타자: 컨택 / 투수: 제구(Control)")
    power: int = Field(..., description="타자: 파워 / 투수: 구위(Stuff)")
    speed: int = Field(..., description="타자: 스피드 / 투수: 구속(Velocity)")

    @property
    def pitcher_stats(self):
        """투수 능력치 매핑"""
        if self.role != Role.PITCHER:
            return None
        return {
            "control": self.contact,
            "stuff": self.power,
            "velocity": self.speed
        }

    @property
    def batter_stats(self):
        """타자 능력치 매핑"""
        if self.role != Role.BATTER:
            return None
        return {
            "contact": self.contact,
            "power": self.power,
            "speed": self.speed
        }

class PlayerState(BaseModel):
    """경기 중 선수의 상태 (체력, 심리 등 - 향후 확장 가능)"""
    character: Character
    current_stamina: int = 100
    condition: str = "NORMAL"

class Team(BaseModel):
    team_id: str
    name: str
    roster: List[PlayerState] = []
    
    def get_pitcher(self) -> PlayerState:
        # 간단한 로직: 로스터의 첫 번째 투수 반환 (향후 로테이션 적용)
        for p in self.roster:
            if p.character.role == Role.PITCHER:
                return p
        return None

    def get_batter(self, order: int) -> PlayerState:
        # 타순에 따른 타자 반환 (투수 제외한 선수들로 구성 가정)
        batters = [p for p in self.roster if p.character.role == Role.BATTER]
        if not batters:
            return None
        return batters[(order - 1) % len(batters)]

# --- Simulation Logic Models ---

class BaseState(BaseModel):
    """주자 상태 (1루, 2루, 3루)"""
    basec1: Optional[PlayerState] = None
    basec2: Optional[PlayerState] = None
    basec3: Optional[PlayerState] = None

class GameState(BaseModel):
    match_id: str
    home_team: Team
    away_team: Team
    
    inning: int = 1
    half: Half = Half.TOP
    outs: int = 0
    strikes: int = 0
    balls: int = 0
    
    home_score: int = 0
    away_score: int = 0
    
    bases: BaseState = Field(default_factory=BaseState)
    
    current_batter_index_home: int = 1
    current_batter_index_away: int = 1
    
    status: SimulationStatus = SimulationStatus.READY
    logs: List[str] = []

    # Multi-Agent Context
    director: DirectorContext = Field(default_factory=DirectorContext)

    def get_current_pitcher(self) -> PlayerState:
        if self.half == Half.TOP:
            return self.home_team.get_pitcher() # 초 공격은 원정팀, 수비(투수)는 홈팀
        else:
            return self.away_team.get_pitcher()

    def get_current_batter(self) -> PlayerState:
        if self.half == Half.TOP:
            return self.away_team.get_batter(self.current_batter_index_away)
        else:
            return self.home_team.get_batter(self.current_batter_index_home)
    
    def get_offense_team(self) -> Team:
        return self.away_team if self.half == Half.TOP else self.home_team
        
    def get_defense_team(self) -> Team:
        return self.home_team if self.half == Half.TOP else self.away_team

    def next_batter(self):
        if self.half == Half.TOP:
            self.current_batter_index_away += 1
        else:
            self.current_batter_index_home += 1

    def get_next_batter_info(self) -> Dict[str, Any]:
        """다음 타자 정보 반환 (프론트엔드 요구사항)"""
        if self.half == Half.TOP:
            idx = self.current_batter_index_away + 1
            batter = self.away_team.get_batter(idx)
        else:
            idx = self.current_batter_index_home + 1
            batter = self.home_team.get_batter(idx)
            
        if batter:
            return {
                "name": batter.character.name,
                "role": "BATTER",
                "stats": batter.character.batter_stats
            }
        return {"name": "None", "stats": {}}


# --- IO / Broadcast Models ---

class SimulationResult(BaseModel):
    """LLM이 생성한 타석 결과"""
    result_code: str # HIT, OUT, HOMERUN, WALK, STRIKEOUT ...
    description: str # 중계 멘트
    runners_advanced: bool = False
    runs_scored: int = 0
    # Detail Info
    pitch_desc: str = "" # 어떤 공을 던졌는지
    hit_desc: str = ""   # 어떻게 쳤는지

class BroadcastData(BaseModel):
    """프론트엔드로 전송될 최종 데이터 구조"""
    match_id: str
    inning: int
    half: str
    outs: int
    home_score: int
    away_score: int
    current_batter: Dict[str, Any]
    current_pitcher: Dict[str, Any]
    result: SimulationResult
    next_batter: Dict[str, Any] # [Feature] 다음 타자 정보 포함
