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
            speed=db_char.speed,
            # [Phase 2]
            mental=db_char.mental,
            stamina=db_char.stamina,
            recovery=db_char.recovery,
            velocity_max=db_char.velocity_max,
            
            pitch_fastball=db_char.pitch_fastball,
            pitch_slider=db_char.pitch_slider,
            pitch_curve=db_char.pitch_curve,
            pitch_changeup=db_char.pitch_changeup,
            pitch_splitter=db_char.pitch_splitter,
            
            eye=db_char.eye,
            clutch=db_char.clutch,
            contact_left=db_char.contact_left,
            contact_right=db_char.contact_right,
            power_left=db_char.power_left,
            power_right=db_char.power_right,
            
            defense_range=db_char.defense_range,
            defense_error=db_char.defense_error,
            defense_arm=db_char.defense_arm,
            position_main=db_char.position_main,
            position_sub=db_char.position_sub
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

    # Track previous state to infer results
    previous_state = {
        "home_score": 0,
        "away_score": 0,
        "outs": 0
    }
    logs_history = []

    # 3. Define Callback to Save Progress
    def on_step(updated_game: sim_models.GameState):
        logger.info(f"Stepped: {updated_game.inning} {updated_game.half} - Outs: {updated_game.outs}")
        
        # Infer what happened
        runs_scored = (updated_game.home_score - previous_state["home_score"]) + \
                      (updated_game.away_score - previous_state["away_score"])
        
        # Update previous state
        previous_state["home_score"] = updated_game.home_score
        previous_state["away_score"] = updated_game.away_score
        previous_state["outs"] = updated_game.outs

        # [Phase 3] Use Engine's Result Object
        # No more text inference (which caused HIT vs OUT mismatch)
        if updated_game.last_result:
            sim_result = updated_game.last_result.model_dump() # Convert Pydantic to dict
            
            # [Frontend Compatibility] Inject params that were removed from Model but might be needed by FE
            sim_result["runs_scored"] = runs_scored
            sim_result["final_bases"] = [
                updated_game.bases.basec1.character.name if updated_game.bases.basec1 else None,
                updated_game.bases.basec2.character.name if updated_game.bases.basec2 else None,
                updated_game.bases.basec3.character.name if updated_game.bases.basec3 else None
            ]
        else:
            # Fallback (Should not happen)
            sim_result = {
                "reasoning": "Fallback (No Result)",
                "result_code": "GO",
                "description": last_log_text,
                "runners_advanced": False,
                "final_bases": [None, None, None],
                "runs_scored": runs_scored,
                "pitch_desc": "",
                "hit_desc": ""
            }

        # Construct BroadcastData
        # Need to map PlayerState to dict
        def p_to_d(p):
            if not p: return {"name": "None", "role": "BATTER", "stats": {}}
            return {
                "name": p.character.name,
                "role": p.character.role,
                "stats": p.character.batter_stats if p.character.role == "BATTER" else p.character.pitcher_stats
            }

        # Runners
        runners = [
            p_to_d(updated_game.bases.basec1) if updated_game.bases.basec1 else None,
            p_to_d(updated_game.bases.basec2) if updated_game.bases.basec2 else None,
            p_to_d(updated_game.bases.basec3) if updated_game.bases.basec3 else None
        ]

        broadcast_data = {
            "match_id": str(match_id),
            "inning": updated_game.inning,
            "half": updated_game.half,
            "outs": updated_game.outs,
            "home_score": updated_game.home_score,
            "away_score": updated_game.away_score,
            "current_batter": p_to_d(updated_game.get_current_batter()),
            "current_pitcher": p_to_d(updated_game.get_current_pitcher()),
            "runners": runners,
            "result": sim_result,
            "next_batter": updated_game.get_next_batter_info()
        }
        
        logs_history.append(broadcast_data)

        # Save to DB
        # We wrap it in a dict as expected by frontend: match.game_state.logs
        match.game_state = { "logs": logs_history }
        match.home_score = updated_game.home_score
        match.away_score = updated_game.away_score
        
        db.commit()
    
    # 4. Run Engine
    try:
        # [Phase 2] Injected DB session
        final_state = engine.run_engine(game_state=game_state, db_session=db, on_step_callback=on_step)
        
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

