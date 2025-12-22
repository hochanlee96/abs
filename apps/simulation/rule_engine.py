from typing import List, Optional, Tuple
from .models import GameState, SimulationResult, PlayerState, Role

class BaseballRuleEngine:
    """
    Deterministic Rule Engine for Baseball.
    Handles state transitions (Runner Advancement, Score, Outs) based on the Event (Result).
    """

    @staticmethod
    def apply_result(game: GameState, result: SimulationResult) -> int:
        """
        Apply the simulation result to the game state.
        Returns the number of runs scored in this play.
        """
        code = result.result_code.upper()
        runs_this_play = 0
        
        current_batter = game.get_current_batter()
        
        # 1. Handle Hits (And Walks)
        if "1B" in code or code == "HIT":
            runs_this_play = BaseballRuleEngine._advance_runners(game, current_batter, bases_advanced=1)
        elif "2B" in code:
            runs_this_play = BaseballRuleEngine._advance_runners(game, current_batter, bases_advanced=2)
        elif "3B" in code:
            runs_this_play = BaseballRuleEngine._advance_runners(game, current_batter, bases_advanced=3)
        elif "HR" in code or "HOMERUN" in code:
            runs_this_play = BaseballRuleEngine._advance_runners(game, current_batter, bases_advanced=4)
        elif "BB" in code or "WALK" in code or "E" == code:
             # 볼넷은 밀어내기 로직이 다름 (무조건 진루가 아니라 1루가 차있을때만)
             # 실책(E)은 MVP 수준에선 일단 1루 진입으로 처리
             runs_this_play = BaseballRuleEngine._handle_walk(game, current_batter)
        
        # 2. Handle Outs
        elif any(x in code for x in ["OUT", "STRIKEOUT", "SO", "GO", "FO", "LO", "FLY", "PO", "K"]):
             runs_this_play = BaseballRuleEngine._handle_out(game)
             
        # 3. Update Score
        if game.half == "TOP":
            game.away_score += runs_this_play
        else:
            game.home_score += runs_this_play
            
        return runs_this_play

    @staticmethod
    def _handle_out(game: GameState) -> int:
        game.outs += 1
        # Sacrifice Fly logic could be added here (if runner on 3rd and < 2 outs)
        # For MVP, assume no advancement on outs (simple rule)
        return 0

    @staticmethod
    def _advance_runners(game: GameState, batter: PlayerState, bases_advanced: int) -> int:
        """
        Move all runners and the batter forward by `bases_advanced`.
        Returns runs scored.
        """
        runs = 0
        
        # Current Runners on bases (BEFORE result)
        # We need to process them to avoid overwriting issues.
        # But for n-base hit, it's simple: everyone moves n bases.
        # Example: 1B -> Runner on 1st goes to 2nd. 2nd to 3rd. 3rd to Home. Batter to 1st.
        
        # Snapshot of current runners
        r3 = game.bases.basec3
        r2 = game.bases.basec2
        r1 = game.bases.basec1
        
        # Reset Bases temporarily
        game.bases.basec1 = None
        game.bases.basec2 = None
        game.bases.basec3 = None
        
        # Function to move a player
        def place_runner(player: PlayerState, current_base: int):
            nonlocal runs
            target_base = current_base + bases_advanced
            
            if target_base >= 4:
                runs += 1
                # Log score?
            else:
                if target_base == 1: game.bases.basec1 = player
                elif target_base == 2: game.bases.basec2 = player
                elif target_base == 3: game.bases.basec3 = player

        # Move existing runners
        if r3: place_runner(r3, 3)
        if r2: place_runner(r2, 2)
        if r1: place_runner(r1, 1)
        
        # Move Batter
        place_runner(batter, 0) # Batter starts at 0 (Home Plate)
        
        return runs

    @staticmethod
    def _handle_walk(game: GameState, batter: PlayerState) -> int:
        """
        Handle Base on Balls (Push logic only if forced).
        """
        runs = 0
        
        # If 1st is empty, batter goes to 1st. Others stay.
        if not game.bases.basec1:
            game.bases.basec1 = batter
            return 0
            
        # If 1st occupied...
        # If 2nd is empty, 1st->2nd. Batter->1st. 3rd stays.
        if not game.bases.basec2:
            game.bases.basec2 = game.bases.basec1
            game.bases.basec1 = batter
            return 0
            
        # If 1st and 2nd occupied...
        # If 3rd empty, 2nd->3rd, 1st->2nd, Batter->1st.
        if not game.bases.basec3:
            game.bases.basec3 = game.bases.basec2
            game.bases.basec2 = game.bases.basec1
            game.bases.basec1 = batter
            return 0
            
        # If Loaded (1,2,3 all occupied) -> Everyone moves 1 base. Run scores.
        runs += 1
        # 3rd -> Home (Score)
        # 2nd -> 3rd
        # 1st -> 2nd
        # Batter -> 1st
        game.bases.basec3 = game.bases.basec2
        game.bases.basec2 = game.bases.basec1
        game.bases.basec1 = batter
        
        return runs
