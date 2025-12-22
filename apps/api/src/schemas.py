from typing import List, Optional, Any, Dict
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from .models import Role, MatchStatus, InningHalf

class CharacterSchema(BaseModel):
    character_id: int
    nickname: str
    is_user_created: bool
    position_main: str
    
    # Stats
    total_games: int
    total_pa: int
    total_ab: int
    total_hits: int
    total_homeruns: int
    total_rbis: int
    total_runs: int
    total_bb: int
    total_so: int
    total_earned_runs: int
    total_outs_pitched: int
    
    model_config = ConfigDict(from_attributes=True)

class TeamPlayerSchema(BaseModel):
    team_player_id: int
    character_id: int
    role: Role
    is_active: bool
    character: CharacterSchema
    
    model_config = ConfigDict(from_attributes=True)

class TeamSchema(BaseModel):
    team_id: int
    team_name: str
    team_players: List[TeamPlayerSchema] = []
    
    model_config = ConfigDict(from_attributes=True)

class MatchSchema(BaseModel):
    match_id: int
    world_id: int
    home_team_id: int
    away_team_id: int
    status: MatchStatus
    home_score: int
    away_score: int
    game_state: Optional[Dict[str, Any]] = None
    
    home_team: Optional[TeamSchema] = None
    away_team: Optional[TeamSchema] = None
    
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
