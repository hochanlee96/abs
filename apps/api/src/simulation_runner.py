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
        players = [p for p in players if p.is_active]
        
        has_pitcher = False
        user_char_id = db_team.user_character_id
        
        # 1st Pass: Create Entities & Assign Roles
        for tp in players:
            db_char = tp.character
            is_user = (db_char.character_id == user_char_id)
            
            if is_user:
                # [Rule] User Character is ALWAYS Batter
                sim_role = sim_models.Role.BATTER
            else:
                # Others: Check Position
                pos = str(db_char.position_main).upper()
                if pos in ["P", "SP", "RP", "CP", "PITCHER"]:
                    sim_role = sim_models.Role.PITCHER
                    has_pitcher = True
                else:
                    sim_role = sim_models.Role.BATTER
            
            sim_char = to_sim_char(db_char, sim_role)
            roster.append(sim_models.PlayerState(character=sim_char))
            
        # 2nd Pass: Safety Check (Ensure at least 1 Pitcher)
        if not has_pitcher and len(roster) > 0:
            # Pick the first NON-USER player to be pitcher
            pitcher_assigned = False
            for p in roster:
                if p.character.character_id != str(user_char_id):
                    p.character.role = sim_models.Role.PITCHER
                    # Update stats mapping for pitcher context if needed (handled by property, but role change is enough)
                    pitcher_assigned = True
                    break
            
            # If still no pitcher (e.g. team has only 1 player and it's the user), force user to pitch (fallback)
            if not pitcher_assigned:
                 roster[0].character.role = sim_models.Role.PITCHER
            
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

            # --- [Phase 3] Update Player Stats in DB ---
            try:
                batter_sim_char = updated_game.get_current_batter()
                if batter_sim_char and batter_sim_char.character.id: # Sim Character has UUID or ID? Wait, engine uses transient objects.
                    # We need to find the DB Character.
                    # sim_models.Character likely has 'id' which maps to DB character_id if we set it up right.
                    # Let's check to_sim_char mapping.
                    # Assuming batter_sim_char.character.data['id'] or sim_models.Character fields.
                    # In `models.py` (sim), Character has `id: str`. In `runner`, we map it.
                    # Let's try to query by name if ID is missing, or rely on `batter_sim_char.character.id`.
                    
                    # NOTE: sim_models.Character might have 'id' as string.
                    char_id = int(batter_sim_char.character.id)
                    db_char = db.query(db_models.Character).filter(db_models.Character.character_id == char_id).first()
                    
                    if db_char:
                        rc = sim_result["result_code"]
                        
                        # At Bats (Walker/Sacrifice excluded usually, but simplified here)
                        if rc not in ["BB", "HBP"]: 
                            db_char.at_bats += 1
                        else:
                            db_char.walks += 1
                            
                        # Hits
                        if rc in ["1B", "2B", "3B", "HOMERUN"]:
                            db_char.hits += 1
                        
                        # Homerun
                        if rc == "HOMERUN":
                            db_char.homeruns += 1
                            db_char.runs += 1 # Batter scores on HR
                        
                        # RBIs
                        db_char.rbis += runs_scored
                        
                        # Strikeout
                        if rc == "SO":
                            db_char.strikeouts += 1
                            
                        # Optimization: Commit later or flush? 
                        # We commit at end of on_step anyway.

                        # --- [Phase 4] Log to PlateAppearance Table (Granular History) ---
                        # This enables "Simulated Stat Calculation" from raw logs as requested.
                        try:
                            # Map Result Code string to Enum if needed, or string.
                            # Schema uses ENUM('SO','BB',...), model likely uses logic.
                            # We assume the string from engine matches the Enum values.
                            
                            # Determine HALF
                            current_half = "TOP" if updated_game.top_bottom == 0 else "BOTTOM" 
                            # Wait, engine uses 0 for top? Let's check or assume "TOP"/"BOTTOM" string matches frontend logic.
                            # Actually updated_game might not have 'top_bottom'. Let's check recent logs.
                            # Log says "half": "TOP".
                            # Let's assume updated_game.half exists or logic is:
                            game_half = "TOP" # Default
                            if hasattr(updated_game, "half"):
                                game_half = updated_game.half
                            elif hasattr(updated_game, "top_bottom"):
                                game_half = "TOP" if updated_game.top_bottom == 0 else "BOTTOM"
                            
                            # Enum Conversion
                            game_half_enum = db_models.InningHalf.TOP if game_half == "TOP" else db_models.InningHalf.BOTTOM
                            
                            final_rc = None
                            try:
                                final_rc = db_models.ResultCode(rc)
                            except ValueError:
                                # Fallback mappings
                                if rc == "OUT" or "OUT" in rc:
                                    final_rc = db_models.ResultCode.GROUND_OUT
                                else:
                                    logger.warning(f"Unknown ResultCode '{rc}', defaulting to GO")
                                    final_rc = db_models.ResultCode.GROUND_OUT

                            # Calculate Sequence safely (count existing for this match + 1)
                            # Using database count is safer for resumption, but slightly slower. 
                            # Given this is a simulation loop, local counter is fine if we init it correctly.
                            # Let's trust auto-increment ID for ordering mostly, but schema requires (match, inning, half, seq).
                            # We can try to query max seq. Or just use a big random number? No.
                            # Let's use a simple query for now.
                            
                            last_seq = db.query(db_models.PlateAppearance.seq)\
                                .filter(db_models.PlateAppearance.match_id == match_id)\
                                .filter(db_models.PlateAppearance.inning == updated_game.inning)\
                                .filter(db_models.PlateAppearance.half == game_half_enum)\
                                .order_by(db_models.PlateAppearance.seq.desc())\
                                .first()
                            
                            new_seq = (last_seq[0] + 1) if last_seq else 1

                            pa_record = db_models.PlateAppearance(
                                match_id=match_id,
                                inning=updated_game.inning,
                                half=game_half_enum,
                                seq=new_seq,
                                batter_character_id=char_id,
                                result_code=final_rc, # Ensure this matches Enum
                                runs_scored=runs_scored,
                                rbi=runs_scored + (1 if rc == "HOMERUN" else 0), # Simplified RBI logic (Batter on HR is +1 RBI usually included in runs_scored? No, runs_scored is total. RBI is runs driven in.)
                                # Wait, if runs_scored=1 (HR), RBI is 1. If 3 run HR, runs_scored=4? No runs_scored is total runs in play.
                                # RBI = runs_scored. (Correct, usually).
                                # Exception: Error? Wild pitch? Unlikely in simple sim.
                                # Let's use rbi=runs_scored for now.
                                outs_added=1 if "O" in str(final_rc.value) or rc == "SO" else 0 
                                # Check if 'O' in 'GO', 'FO', 'SO'. Yes. '1B' no.
                            )
                            db.add(pa_record)
                        except Exception as e_pa:
                            logger.error(f"Failed to log PlateAppearance: {e_pa}")

            except Exception as e:
                logger.error(f"Stats Update Error: {e}")

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

