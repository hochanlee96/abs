import sys
import os
import json
import logging
from sqlalchemy.orm import Session
from datetime import datetime

# Adjust path to import simulation module
# Docker volume mount point: /app/simulation_module
sys.path.append("/app/simulation_module")

try:
    from simulation_module import engine
    from simulation_module import models as sim_models
except ImportError as e:
    logging.warning(f"Simulation module not found. Is it mounted correctly? {e}")
    engine = None
    sim_models = None

from . import models as db_models
from .models import MatchStatus, ResultCode, InningHalf

logger = logging.getLogger(__name__)

def run_match_background(match_id: int, db: Session):
    """
    Background task to run the simulation for a given match_id.
    """
    logger.info(f"Starting simulation for match_id={match_id}...")
    
    if not engine or not sim_models:
        logger.error("Simulation engine not loaded. Aborting.")
        return

    # 1. Load Match & Entities from DB
    match = db.query(db_models.Match).filter(db_models.Match.match_id == match_id).first()
    if not match:
        logger.error(f"Match {match_id} not found.")
        return

    # Update Status to IN_PROGRESS
    match.status = MatchStatus.IN_PROGRESS
    match.started_at = datetime.utcnow()
    db.commit()

    # 2. Convert DB Models to Simulation Models
    # We need to build sim_models.GameState
    
    # Helper to convert Character -> sim_models.Character
    def to_sim_char(db_char: db_models.Character, role: sim_models.Role) -> sim_models.Character:
        return sim_models.Character(
            character_id=str(db_char.character_id),
            name=db_char.nickname,
            role=role,
            contact=db_char.contact,
            power=db_char.power,
            speed=db_char.speed
        )

    # Helper to build Team roster
    # Simple logic: Assign roles based on DB or rule (first is Pitcher for now)
    # Ideally, DB TeamPlayer table has roles.
    def build_roster(db_team: db_models.Team) -> list[sim_models.PlayerState]:
        roster = []
        players = db_team.team_players
        # Filter active players if needed
        players = [p for p in players if p.is_active]
        
        # Sort or select specific players? For now just take them all.
        # Ensure at least one pitcher and batters.
        # If roles are not well defined in MVP, assume first 1 is Pitcher, rest Batters
        
        for idx, tp in enumerate(players):
            db_char = tp.character
            # Map DB Role to Sim Role
            # Infer Position: Index 0 is Pitcher, rest are Batters
            sim_role = sim_models.Role.PITCHER if idx == 0 else sim_models.Role.BATTER
            
            sim_char = to_sim_char(db_char, sim_role)
            roster.append(sim_models.PlayerState(character=sim_char))
            
        return roster

    home_roster = build_roster(match.home_team)
    away_roster = build_roster(match.away_team)
    
    home_team = sim_models.Team(
        team_id=str(match.home_team_id),
        name=match.home_team.team_name,
        roster=home_roster
    )
    
    away_team = sim_models.Team(
        team_id=str(match.away_team_id),
        name=match.away_team.team_name,
        roster=away_roster
    )
    
    # Initial Game State
    game_state = sim_models.GameState(
        match_id=str(match.match_id),
        home_team=home_team,
        away_team=away_team,
        status=sim_models.SimulationStatus.PLAYING
    )

    # 3. Define Callback to Save Progress
    def on_step(updated_game: sim_models.GameState):
        logger.info(f"Stepped: {updated_game.inning} {updated_game.half} - Outs: {updated_game.outs}")
        
        # A. Save Transient Game State (JSON)
        # We need to serialize Pydantic model to dict
        # Using model_dump (v2) or dict (v1). Requirements says pydantic used.
        state_dump = updated_game.model_dump(mode='json')
        match.game_state = state_dump
        match.home_score = updated_game.home_score
        match.away_score = updated_game.away_score
        
        # B. Save Plate Log (if a result occurred)
        # The engine appends logs. We can check the last log or use the structured last_result if passed?
        # The callback only gets updated_game. 
        # But 'updated_game.logs' has strings. 
        # Better approach: The engine state has 'last_result'.
        # But our callback signature in engine.py only passes `updated_game`.
        # *Self-Correction*: `on_step` in `engine.py` is called with `updated_game`.
        # Accessing the structured result might require modifying engine to pass it, 
        # OR we infer it from the fact that a step happened.
        # Ideally, we want to save the `PlateAppearance` row here.
        
        # Let's assume for now we just save the game_state JSON which is enough for the frontend "progress".
        # Saving PlateAppearance requires the `SimulationResult` object which dictates `result_code`.
        # Engine refactor in previous step:
        # `if on_step_callback: on_step_callback(updated_game)`
        # It doesn't pass the result.
        # I should probably update the DB regardless.
        
        db.commit()
    
    # 4. Run Engine
    try:
        final_state = engine.run_engine(game_state, on_step_callback=on_step)
        
        # Match Finished
        match.status = MatchStatus.FINISHED
        match.finished_at = datetime.utcnow()
        if final_state.home_score > final_state.away_score:
            match.winner_team_id = match.home_team_id
            match.loser_team_id = match.away_team_id
        elif final_state.away_score > final_state.home_score:
            match.winner_team_id = match.away_team_id
            match.loser_team_id = match.home_team_id
            
        db.commit()
        logger.info(f"Simulation finished for match {match_id}")
        
    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        # db.rollback() # Safe to rollback or just log?
        match.status = MatchStatus.CANCELED # Or keep as IN_PROGRESS to retry?
        db.commit()

