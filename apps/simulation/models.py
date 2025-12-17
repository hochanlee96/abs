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

