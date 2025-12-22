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

def run_match_background(match_id: int, _db: Session = None):
    """
    Background task to run the simulation for a given match_id.
    Note: We ignore the passed _db (request-scoped) and create a new session
    to avoid 'Session is closed' errors in background execution.
    """
    # Import locally to avoid circular imports if any, or just ensure it's available
    from .db import SessionLocal

    logger.info(f"Starting simulation for match_id={match_id}...")
    
    if not engine or not sim_models:
        logger.error("Simulation engine not loaded. Aborting.")
        return

    db = SessionLocal()
    # 1. Load Match & Entities from DB
    match = db.query(db_models.Match).filter(db_models.Match.match_id == match_id).first()
    if not match:
        logger.error(f"Match {match_id} not found.")
        db.close()
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
        # Explicitly sort by team_player_id to ensure a stable batting order
        players = sorted(db_team.team_players, key=lambda tp: tp.team_player_id)
        # Filter active players if needed
        players = [p for p in players if p.is_active]
        
        # Sort or select specific players? For now just take them all.
        # Ensure at least one pitcher and batters.
        # If roles are not well defined in MVP, assume first 1 is Pitcher, rest Batters
        
        for idx, tp in enumerate(players):
            db_char = tp.character
            # Map DB Role to Sim Role
            # Check actual position string
            pos_main = db_char.position_main.upper()
            if "P" in pos_main or "PITCHER" in pos_main:
                sim_role = sim_models.Role.PITCHER
            else:
                sim_role = sim_models.Role.BATTER
            
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
        "outs": 0,
        "inning": 1,
        "half": "TOP"
    }
    logs_history = []

    # 3. Define Callback to Save Progress
    def on_step(updated_game: sim_models.GameState):
        logger.info(f"Stepped: {updated_game.inning} {updated_game.half} - Outs: {updated_game.outs}")
        
        # Calculate changes/deltas based on PREVIOUS state (before this step)
        runs_scored = (updated_game.home_score - previous_state["home_score"]) + \
                      (updated_game.away_score - previous_state["away_score"])
        
        # Calculate Outs Added
        # If inning/half changed, it means we reached 3 outs in the previous half
        prev_half = previous_state["half"]
        prev_inning = previous_state["inning"]
        prev_outs = previous_state["outs"]
        
        outs_added = 0
        if updated_game.half != prev_half or updated_game.inning != prev_inning:
            outs_added = 3 - prev_outs
        else:
            outs_added = updated_game.outs - prev_outs

        # [Stats Update: Pitcher] - Update regardless of result object presence
        # Because outs/runs are derived from state deltas
        if runs_scored > 0 or outs_added > 0:
            try:
                # Identifying the pitcher who threw the ball (Defensive team of prev_half)
                prev_pitcher = None
                if prev_half == "TOP": #/ TOP means Away Batting, Home Pitching
                     # Pitcher is Home Team
                     prev_pitcher = updated_game.home_team.get_pitcher()
                else:
                     # Pitcher is Away Team
                     prev_pitcher = updated_game.away_team.get_pitcher()
                
                if prev_pitcher:
                    p_char_id = int(prev_pitcher.character.character_id)
                    db_pitcher = db.query(db_models.Character).filter_by(character_id=p_char_id).first()
                    if db_pitcher:
                        if runs_scored > 0:
                            db_pitcher.total_earned_runs += runs_scored
                            logger.info(f"DEBUG: Pitcher {p_char_id} ER += {runs_scored}")
                        if outs_added > 0:
                            db_pitcher.total_outs_pitched += outs_added
                            logger.info(f"DEBUG: Pitcher {p_char_id} ({db_pitcher.nickname}) Outs += {outs_added}. Total IP: {db_pitcher.total_outs_pitched/3:.1f}")
                        
                        db.add(db_pitcher)
            except Exception as e:
                logger.error(f"Failed to update pitcher stats: {e}")
            
        # Update previous state for NEXT step
        previous_state["home_score"] = updated_game.home_score
        previous_state["away_score"] = updated_game.away_score
        previous_state["outs"] = updated_game.outs
        previous_state["inning"] = updated_game.inning
        previous_state["half"] = updated_game.half

        # [Phase 3] Use Engine's Result Object
        # No more text inference (which caused HIT vs OUT mismatch)
        if updated_game.last_result:
            sim_result = updated_game.last_result.model_dump() # Convert Pydantic to dict
            
            # [Frontend Compatibility] Inject params that were removed from Model but might be needed by FE
            sim_result["runs_scored"] = runs_scored
            # Update the model instance as well
            updated_game.last_result.runs_scored = runs_scored
            
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
                "description": "Simulation Error Fallback", 
                "runners_advanced": False,
                "final_bases": [None, None, None],
                "runs_scored": runs_scored,
                "pitch_desc": "",
                "hit_desc": ""
            }

        # [Stats Update] - Sync with DB Character
        if updated_game.last_result:
            try:
                # Identify Batter (The one who JUST finished)
                # Note: valid only if next_batter() was called in update_state_node just before this callback
                prev_batter = None
                if updated_game.half == "TOP": #/ sim_models.Half.TOP is "TOP" string enum
                    # Away Team was batting
                    idx = updated_game.current_batter_index_away - 1
                    prev_batter = updated_game.away_team.get_batter(idx)
                    logger.info(f"DEBUG: current_half TOP, Away Batter Idx {idx}, Name: {prev_batter.character.name if prev_batter else 'None'}")
                else:
                    # Home Team was batting
                    idx = updated_game.current_batter_index_home - 1
                    prev_batter = updated_game.home_team.get_batter(idx)
                    logger.info(f"DEBUG: current_half BOTTOM, Home Batter Idx {idx}, Name: {prev_batter.character.name if prev_batter else 'None'}")

                batter_state = prev_batter

                # Determine Result Code
                r_code = updated_game.last_result.result_code # String e.g. "1B", "GO"
                logger.info(f"DEBUG: Result Code {r_code}")
                
                if batter_state:
                    char_id = int(batter_state.character.character_id) # Ensure int
                    db_char = db.query(db_models.Character).filter_by(character_id=char_id).first()
                    
                    if db_char:
                        logger.info(f"DEBUG: Found DB Character {char_id} ({db_char.nickname}). Current: PA={db_char.total_pa}, H={db_char.total_hits}, AB={db_char.total_ab}")
                        db_char.total_pa += 1
                        
                        # Hit
                        if r_code in ["1B", "2B", "3B", "HR", "HIT", "SINGLE", "DOUBLE", "TRIPLE", "HOMERUN", "HOME_RUN"]:
                            logger.info(f"DEBUG: Match HIT for {char_id} - code: {r_code}")
                            db_char.total_ab += 1
                            db_char.total_hits += 1
                            if r_code in ["HR", "HOMERUN", "HOME_RUN"]:
                                db_char.total_homeruns += 1
                                db_char.total_rbis += runs_scored # Home run implies RBI for self + runners
                            else:
                                if runs_scored > 0:
                                    db_char.total_rbis += runs_scored
                        
                        # Out
                        elif r_code in ["GO", "FO", "LO", "PO", "SO", "STRIKEOUT", "OUT", "FLY_OUT", "GROUND_OUT", "LINE_OUT", "POP_OUT", "FLY", "FLYOUT", "K", "STRIKE_OUT", "K_STRIKE_OUT", "LOOKING_STRIKEOUT", "SWINGING_STRIKEOUT"]:
                            db_char.total_ab += 1
                            if r_code in ["SO", "STRIKEOUT"]:
                                db_char.total_so += 1
                        
                        # Walk / Dead Ball
                        elif r_code in ["BB", "IBB", "HBP", "WALK", "BASE_ON_BALLS", "HIT_BY_PITCH"]:
                             db_char.total_bb += 1
                             # No AB increment
                             if runs_scored > 0: 
                                 db_char.total_rbis += runs_scored 

                        # Save
                        db.add(db_char)
                        logger.info(f"DEBUG: Stats updated. Post-update: PA={db_char.total_pa}, Hits={db_char.total_hits}")
                        
                        # [Audit] Create Plate Appearance Record
                        pa = db_models.PlateAppearance(
                            match_id=match_id,
                            inning=updated_game.inning,
                            half=db_models.InningHalf.TOP if updated_game.half == "TOP" else db_models.InningHalf.BOTTOM,
                            seq=len(logs_history) + 1, 
                            batter_character_id=char_id,
                            result_code=str(r_code) # Ensure string
                        )
                        db.add(pa)
                        logger.info(f"DEBUG: PA record created for {char_id} code={r_code}")
                    else:
                        logger.error(f"DEBUG: DB Char {char_id} NOT FOUND")
                else:
                    logger.error("DEBUG: Batter State is None")

            except Exception as e:
                logger.error(f"Failed to update stats: {e}")
        else:
            logger.warning("DEBUG: updated_game.last_result is None")
            # [Stats Update: Batter Fallback]
            # If no result object but Outs increased, we assume a generic OUT for the batter.
            # This handles the "merged 3rd out" case.
            if outs_added > 0:
                try:
                    prev_batter = None
                    if updated_game.half == "TOP":
                        idx = updated_game.current_batter_index_away - 1
                        prev_batter = updated_game.away_team.get_batter(idx)
                    else:
                        idx = updated_game.current_batter_index_home - 1
                        prev_batter = updated_game.home_team.get_batter(idx)
                    
                    if prev_batter:
                        char_id = int(prev_batter.character.character_id)
                        db_char = db.query(db_models.Character).filter_by(character_id=char_id).first()
                        if db_char:
                            db_char.total_pa += 1
                            db_char.total_ab += 1
                            # Assume generic out (no SO/K recorded)
                            db.add(db_char)
                            logger.info(f"DEBUG: Fallback Batter Update: Out recorded for {char_id} (No Result Object)")
                            
                            # Optional: Create generic PA record
                            pa = db_models.PlateAppearance(
                                match_id=match_id,
                                inning=updated_game.inning, 
                                half=db_models.InningHalf.TOP if updated_game.half == "TOP" else db_models.InningHalf.BOTTOM,
                                seq=len(logs_history) + 1,
                                batter_character_id=char_id,
                                result_code="OUT" # Generic
                            )
                            db.add(pa)
                except Exception as e:
                    logger.error(f"Fallback Batter Update Failed: {e}")

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
            
        # [Stats Update] Increment total_games for all participating characters
        # We can iterate through both team rosters and increment total_games
        for player in game_state.home_team.roster + game_state.away_team.roster:
            try:
                char_id = int(player.character.character_id)
                db_char = db.query(db_models.Character).filter_by(character_id=char_id).first()
                if db_char:
                    db_char.total_games += 1
                    logger.info(f"Incremented total_games for character {char_id}: {db_char.total_games}")
                    db.add(db_char)
            except Exception as e:
                logger.error(f"Failed to increment total_games for character: {e}")

        db.commit()
        logger.info(f"Simulation finished for match {match_id}")
        
    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        # db.rollback() # Safe to rollback or just log?
        match.status = MatchStatus.CANCELED # Or keep as IN_PROGRESS to retry?
        db.commit()
    finally:
        db.close()
