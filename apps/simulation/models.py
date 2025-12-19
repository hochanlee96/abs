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
    change_pitcher: bool = Field(default=False, description="투수 교체 여부 (체력 저하 시 True)")
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
    # Ability Stats (Basic)
    contact: int = Field(..., description="타자: 컨택 / 투수: 제구(Control)")
    power: int = Field(..., description="타자: 파워 / 투수: 구위(Stuff)")
    speed: int = Field(..., description="타자: 스피드 / 투수: 구속(Velocity)")

    # --- [Phase 2] Extended Stats ---
    # Common
    mental: int = Field(50, description="멘탈/위기관리 (0-100)")
    
    # Pitcher Specific
    stamina: int = Field(100, description="체력 (투구수 영향)")
    recovery: int = Field(50, description="회복력")
    velocity_max: int = Field(145, description="최고 구속")
    
    pitch_fastball: int = Field(50, description="직구 숙련도")
    pitch_slider: int = Field(50, description="슬라이더 숙련도")
    pitch_curve: int = Field(50, description="커브 숙련도")
    pitch_changeup: int = Field(50, description="체인지업 숙련도")
    pitch_splitter: int = Field(50, description="스플리터 숙련도")
    
    # Batter Specific
    eye: int = Field(50, description="선구안")
    clutch: int = Field(50, description="득점권 타율 보정")
    
    contact_left: int = Field(50, description="좌투수 상대 컨택")
    contact_right: int = Field(50, description="우투수 상대 컨택")
    power_left: int = Field(50, description="좌투수 상대 파워")
    power_right: int = Field(50, description="우투수 상대 파워")
    
    # Fielder Specific
    defense_range: int = Field(50, description="수비 범위")
    defense_error: int = Field(50, description="포구 실책 빈도 (낮을수록 좋음)")
    defense_arm: int = Field(50, description="송구력")
    
    position_main: str = Field("DH", description="주 포지션")
    position_sub: Optional[str] = Field(None, description="부 포지션")

    @property
    def pitcher_stats(self):
        """투수 능력치 매핑 (확장)"""
        if self.role != Role.PITCHER:
            return None
        return {
            "control": self.contact, # 기존 유지
            "stuff": self.power,     # 기존 유지
            "velocity": self.speed,  # 기존 유지
            "stamina": self.stamina,
            "mental": self.mental,
            "pitches": {
                "fastball": self.pitch_fastball,
                "slider": self.pitch_slider,
                "curve": self.pitch_curve,
                "changeup": self.pitch_changeup,
                "splitter": self.pitch_splitter
            }
        }

    @property
    def batter_stats(self):
        """타자 능력치 매핑 (확장)"""
        if self.role != Role.BATTER:
            return None
        return {
            "contact": self.contact,
            "power": self.power,
            "speed": self.speed,
            "eye": self.eye,
            "clutch": self.clutch,
            "defense": {
                "range": self.defense_range,
                "error": self.defense_error,
                "arm": self.defense_arm
            }
        }

class PlayerState(BaseModel):
    """경기 중 선수의 상태 (체력, 심리 등 - 향후 확장 가능)"""
    character: Character
    current_stamina: int = 100
    condition: str = "NORMAL"
    pitch_count: int = 0 # 투구 수

class Team(BaseModel):
    team_id: str
    name: str
    roster: List[PlayerState] = []
    current_pitcher_index: int = 0 # 현재 등판 중인 투수의 인덱스 (roster 내의 PITCHER 필터링 기준 아님, 전체 로스터 기준이 편함)
    # 하지만 roster엔 타자도 섞여있음. PITCHER 역할인 선수들만 모아놓은 인덱스 관리가 필요.
    
    def get_pitchers(self) -> List[PlayerState]:
        return [p for p in self.roster if p.character.role == Role.PITCHER]

    def get_pitcher(self) -> PlayerState:
        """현재 마운드에 있는 투수 반환"""
        pitchers = self.get_pitchers()
        if not pitchers:
            return None
        # 인덱스 보호
        if self.current_pitcher_index >= len(pitchers):
            self.current_pitcher_index = len(pitchers) - 1
        return pitchers[self.current_pitcher_index]
    
    def change_pitcher(self) -> bool:
        """다음 투수로 교체 (성공 시 True)"""
        pitchers = self.get_pitchers()
        if self.current_pitcher_index + 1 < len(pitchers):
            self.current_pitcher_index += 1
            return True
        return False

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
    
    # [Data Integrity] Engine's last result directly embedded
    last_result: Optional['SimulationResult'] = None

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
    reasoning: str = Field(description="판정 추론 과정 (STEP-BY-STEP Thinking)") # CoT
    result_code: str # HIT, OUT, HOMERUN, WALK, STRIKEOUT ...
    description: str # 중계 멘트
    runners_advanced: bool = False
    
    # LLM Decides Bases (Rule-Free)
    # [1루주자이름/None, 2루주자이름/None, 3루주자이름/None]
    # 이름 문자열로 받아서 engine에서 매핑
    final_bases: List[Optional[str]] = Field(default_factory=lambda: [None, None, None])
    runs_scored: int = 0
    
    # Detail Info
    pitch_desc: str = "" # 어떤 공을 던졌는지
    hit_desc: str = ""   # 어떻게 쳤는지

class ValidatorResult(BaseModel):
    """검증 에이전트(Rule Expert)의 판정 결과"""
    is_valid: bool = Field(..., description="야구 규칙 및 논리적 정합성 준수 여부")
    reasoning: str = Field(..., description="검증 결과에 대한 근거 (CoT)")
    error_type: Optional[str] = Field(None, description="오류 유형 (LogicError, RuleViolation, Hallucination)")
    correction_suggestion: Optional[str] = Field(None, description="수정 제안 (필요 시)")

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
    runners: List[Optional[Dict[str, Any]]] # [1루주자, 2루주자, 3루주자] 정보 (없으면 None)
    result: SimulationResult
    next_batter: Dict[str, Any] # [Feature] 다음 타자 정보 포함
