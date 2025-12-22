import os
import random
import json
from typing import TypedDict, Annotated, List, Dict, Optional, Any
from dotenv import load_dotenv

# LangChain / LangGraph
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langgraph.graph import StateGraph, END

# Local Imports
from .models import (
    GameState, SimulationResult, Half, SimulationStatus, BroadcastData,
    DirectorContext, ManagerDecision, PitcherDecision, BatterDecision,
    Weather, UmpireZone, TeamStrategy,
    PitchType, PitchLocation, BattingStyle, Role, ValidatorResult
)
from .dummy_generator import init_dummy_game
from .rule_engine import BaseballRuleEngine

# Load Env
load_dotenv()

# --- LLM Setup ---
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

# --- State for Graph ---
class SimState(TypedDict):
    """Simulation State"""
    game: GameState
    director_ctx: DirectorContext
    
    home_manager_decision: ManagerDecision
    away_manager_decision: ManagerDecision
    
    pitcher_decision: PitcherDecision
    batter_decision: BatterDecision
    
    last_result: SimulationResult
    validator_result: Optional['ValidatorResult'] # 추가된 검증 결과 | None
    
    retry_count: int # 검증 실패 시 재시도 횟수 tracking
    db_session: Optional[Any] # DB Session for saving results

# --- Prompt Templates (Agents Thinking) ---

DIRECTOR_PROMPT = """
당신은 야구 경기의 총괄 감독(Director)이자 심판장입니다.
현재 경기의 환경(날씨, 바람, 심판 존)을 결정하거나 유지하세요.

[현재 상황]
- {inning}회 {half}
- 날씨: {current_weather}
- 심판 판정: {current_zone}

비가 오면 경기력에 영향을 줄 수 있습니다. 심판의 판정 구역이 넓거나 좁아질 수 있습니다.
적절한 환경을 설정하세요.
"""

MANAGER_PROMPT = """
당신은 {team_name}의 감독(Manager)입니다.
현재 경기 상황을 분석하고 작전을 지시하세요.

[경기 상황]
- 점수 차: {score_diff} (우리 팀 {my_score} : 상대 {opp_score})
- 이닝: {inning}회 {half}
- 아웃: {outs}, 주자: {runners}
- 현재 타자: {batter_name} (능력: {batter_stats})
- 상대 투수/타자: {opponent_name}

[투수 상태 (우리 팀 수비 시)]
- 현재 투수: {current_pitcher_name}
- 투구 수: {pitch_count}
- 남은 체력: {current_stamina} / {max_stamina}
(체력이 30 이하로 떨어지거나 난타당하면 교체를 고려하세요.)

[가능한 작전]
- NORMAL: 정상 플레이
- BUNT: 번트 시도 (주자가 있을 때, 접전 상황)
- HIT_AND_RUN: 히트 앤드 런 (주자가 빠르고 타자가 컨택이 좋을 때)
- INFIELD_IN: 전진 수비 (3루 주자 실점을 막아야 할 때)
- LONG_BALL: 장타 노림 (점수 차가 클 때, 파워 히터)

당신의 작전과 그 이유, 그리고 **투수 교체 여부**를 결정하세요.
"""

PITCHER_PROMPT = """
당신은 투수(Pitcher) {name}입니다.
감독의 작전, 타자의 약점, 나의 능력치를 고려해 공을 던지세요.

[나의 능력치]
- 구속 {velocity}, 구위 {stuff}, 제구 {control}

[상대 타자]
- 이름: {batter_name}
- 통계: 컨택 {contact}, 파워 {power}, 스피드 {speed}

[감독 작전]
- {strategy}

[의사결정 요소]
1. 구종 선택 (직구, 슬라이더, 커브 등)
2. 코스 선택 (몸쪽, 바깥쪽, 위, 아래, 한가운데)
3. 완급 조절 (전력 투구, 맞춰 잡기)

제구력이 낮으면 의도한 코스로 가지 않을 수 있습니다(실투).
어떤 공을 어디에 던질지 결정하세요.
"""

BATTER_PROMPT = """
당신은 타자(Batter) {name}입니다.
감독의 작전, 투수의 패턴, 나의 능력치를 고려해 타격 준비를 하세요.

[나의 능력치]
- 컨택 {contact}, 파워 {power}, 스피드 {speed}

[상대 투수]
- 이름: {pitcher_name}
- 통계: 구속 {velocity}, 구위 {stuff}, 제구 {control}

[감독 작전]
- {strategy}

[의사결정 요소]
1. 노림수 (직구를 노릴지, 변화구를 노릴지)
2. 타격 포인트 (당겨칠지, 밀어칠지)
3. 스타일 (적극적 초구 공략 vs 신중하게 공 보기)

어떤 공을 노리고 어떻게 대처할지 결정하세요.
"""

RESOLVER_PROMPT = """
당신은 고도로 훈련된 **야구 시뮬레이션 심판(Umpire)이자 물리 엔진**입니다.
주어진 데이터(선수 능력, 상황, 작전)와 **직전 검증 실패 피드백**를 분석하여 **가장 현실적이고 개연성 있는 경기 결과**를 도출하세요.

**[Realistic Balance: Game Balance]**
- **"야구는 흐름(Flow)의 스포츠입니다."**:
    - **Base Rate**: 기본적으로는 **타율 0.250 ~ 0.280** (아웃 70-75%)을 지향합니다.
    - **Dynamic Modifiers (중요)**: 상황에 따라 확률을 과감하게 조정하세요.
        1.  **Pitcher Stamina (체력)**:
            - **High (80+)**: 투수 압도. 안타 확률 매우 낮음.
            - **Medium (40-79)**: 대등한 승부.
            - **Stamina Low (<40)**: **안타 확률 제한적 증가 (최대 타율 .300).** 투수가 지쳤어도 배팅볼 아님. **난타전 절대 금지.**
        2.  **Clutch (득점권)**: `clutch` 스탯이 높은 타자는 주자가 있을 때 타율 보정.
        3.  **Scoreless Streak**: 5이닝 이상 0-0이면, **타자들의 집중력이 올라가며 안타 확률을 소폭 상향**하여 경기의 균형을 깹니다.

    **[Outcome Distribution Guide (Modified by Stamina)]**
    - **Stamina High**: **아웃 80% / 안타 10% / 사사구 10%** (투수 우위)
    - **Stamina Normal**: **아웃 75% / 안타 18% / 사사구 7%** (다소 투고타저 지향)
    - **Stamina Low**: **아웃 65% / 단타(1B) 25% / 장타(2B/HR) 3% / 사사구 7%** (절대 안타가 50%를 넘지 말 것)

3.  **Specific Description**
    - 투수 체력이 낮을 때는 "밋밋하게 들어간 공", "스피드가 떨어진 직구" 등을 묘사하며 안타를 허용하세요.
    - 잘 맞은 타구여도 야수 정면이면 아웃입니다. (단, 체력 저하 시에는 수비수 키를 넘기는 묘사 선호)

4.  **Reasoning Guide (CoT)**
    1.  **Check Stamina**: 투수 체력이 40 미만인가? -> 맞다면 'Hit' 가능성 최우선 검토.
    2.  **Batter Skill**: 타자의 Contact/Power가 투수 구위를 압도하는가?
    3.  **Final Decision**: 위 조건들을 종합하여 '무조건 아웃'이 아닌, 합리적인 흐름 선택.
4.  **Feedback Check**: 이전 검증 피드백이 있다면 반드시 반영.

**[Output Format]**
- `result_code`: `1B`, `2B`, `3B`, `HR`, `BB`, `SO`, `GO`, `FO`, `LO`, `E` 중 택 1.
- `description`: 생생한 문장형 묘사.

**[Current Game Context]**
{game_info}


**[Few-shot Examples]**
*   **Case 1 (땅볼 아웃)**
    *   `result_code`: "GO"
    *   `description`: "유격수 깊은 타구! 잡아서 1루에... 아웃입니다! 간발의 차였습니다."
*   **Case 2 (라인드라이브 아웃)**
    *   `result_code`: "LO"
    *   `description`: "잘 맞은 타구! 하지만 2루수 정면으로 향하며 직선타로 물러납니다."
*   **Case 3 (2루타)**
    *   `result_code`: "2B"
    *   `description`: "우익수 키를 넘기는 큼지막한 타구! 타자 주자는 1루를 돌아 2루까지 여유 있게 들어갑니다."
*   **Case 4 (홈런 - 파워히터)**
    *   `result_code`: "HR"
    *   `description`: "잡아당겼습니다! 이 타구는... 담장! 담장을 넘어갑니다! 장외로 사라지는 초대형 홈런!"

[입력 데이터]
[환경] 날씨: {weather}, 바람: {wind}, 심판 존: {zone}
[상황] 아웃: {outs}, {runners_status}
[수비] {defense_lineup}

[투수 {pitcher_name}] {pitch_type}({pitch_location}) | 구속 {velocity}, 구위 {stuff}, 제구 {control}, 멘탈 {mental}
[타자 {batter_name}] 노림수 {aim_type}, 코스 {aim_location} | 컨택 {contact}, 파워 {power}, 스피드 {speed}

[검증 피드백 (이전 시도 실패 사유)]
{validator_feedback}

위 정보를 종합하여 결과를 JSON으로 출력하세요.
"""


VALIDATOR_PROMPT = """
당신은 **야구 기록 검증관(Scorer)**입니다.
시뮬레이션 결과가 논리적으로 타당한지 검증하세요. (주자 이동이나 점수 계산은 검증하지 않습니다. 오직 '판정 자체'만 봅니다.)

**[필수 검증 항목]**
1.  **Result Consistency**: `result_code`와 `description`이 일치하는가?
    - **CRITICAL**: **먼저 `result_code`를 확정하고, 그에 맞춰 `description`을 작성하세요.** (예: 2B인데 "홈런성 타구" 묘사 금지)
    *   Code는 `GO`(땅볼)인데 설명은 "담장을 넘깁니다!"면 Invalid.
2.  **Context Consistency**: 상황에 맞는 결과인가?
    *   **Context Consistency**: 상황에 맞는 결과인가?
    *   예: 투수가 `WALK` 상태가 아닌데 `BB`가 나오거나 하진 않는지(사실 이건 허용되지만, 터무니없는 상황 체크).

[직전 상황]
- 아웃: {outs}, 주자: {runners_before}

[시뮬레이션 판정 결과]
- 결과: {result_code} ({description})

문제가 있다면 `is_valid: false`와 `correction_suggestion`을 작성하세요. 문제 없으면 `is_valid: true`.
"""

# --- Nodes ---

def director_node(state: SimState):
    """경기 환경 설정"""
    game = state["game"]
    ctx = state.get("director_ctx", DirectorContext())
    
    prompt = ChatPromptTemplate.from_template(DIRECTOR_PROMPT)
    chain = prompt | llm.with_structured_output(DirectorContext)
    
    new_ctx = chain.invoke({
        "inning": game.inning,
        "half": game.half,
        "current_weather": ctx.weather,
        "current_zone": ctx.umpire_zone
    })
    
    return {"director_ctx": new_ctx}

def manager_node(state: SimState):
    """양 팀 감독의 작전 지시"""
    import traceback
    try:
        game = state["game"]
        
        # Home Manager
        prompt = ChatPromptTemplate.from_template(MANAGER_PROMPT)
        manager_chain = prompt | llm.with_structured_output(ManagerDecision)
        
        runners = []
        if game.bases.basec1: runners.append("1루")
        if game.bases.basec2: runners.append("2루")
        if game.bases.basec3: runners.append("3루")
        runners_str = ",".join(runners) if runners else "없음"
        
        # Home Manager Context
        home_p = game.home_team.get_pitcher()
        home_decision = manager_chain.invoke({
            "team_name": game.home_team.name,
            "score_diff": game.home_score - game.away_score,
            "my_score": game.home_score,
            "opp_score": game.away_score,
            "inning": game.inning,
            "half": game.half,
            "outs": game.outs,
            "runners": runners_str,
            "batter_name": game.get_current_batter().character.name,
            "batter_stats": game.get_current_batter().character.batter_stats,
            "opponent_name": game.get_current_pitcher().character.name,
            "current_pitcher_name": home_p.character.name,
            "pitch_count": home_p.pitch_count,
            "current_stamina": home_p.current_stamina,
            "max_stamina": home_p.character.stamina
        })

        # Away Manager Context
        away_p = game.away_team.get_pitcher()
        away_decision = manager_chain.invoke({
            "team_name": game.away_team.name,
            "score_diff": game.away_score - game.home_score,
            "my_score": game.away_score,
            "opp_score": game.home_score,
            "inning": game.inning,
            "half": game.half,
            "outs": game.outs,
            "runners": runners_str,
            "batter_name": game.get_current_batter().character.name,
            "batter_stats": game.get_current_batter().character.batter_stats,
            "opponent_name": game.get_current_pitcher().character.name,
            "current_pitcher_name": away_p.character.name,
            "pitch_count": away_p.pitch_count,
            "current_stamina": away_p.current_stamina,
            "max_stamina": away_p.character.stamina
        })

        return {
            "home_manager_decision": home_decision,
            "away_manager_decision": away_decision
        }
    except Exception as e:
        err_msg = traceback.format_exc()
        with open("error_log.txt", "w", encoding="utf-8") as f:
            f.write(err_msg)
        print(f"Error in manager_node: {e}")
        raise e

def pitcher_node(state: SimState):
    """투수 의사결정"""
    game = state["game"]
    pitcher = game.get_current_pitcher()
    batter = game.get_current_batter()
    
    strategy = state["home_manager_decision"].defense_strategy if game.half == Half.TOP else state["away_manager_decision"].defense_strategy
    
    prompt = ChatPromptTemplate.from_template(PITCHER_PROMPT)
    chain = prompt | llm.with_structured_output(PitcherDecision)
    
    decision = chain.invoke({
        "name": pitcher.character.name,
        "velocity": pitcher.character.pitcher_stats["velocity"],
        "stuff": pitcher.character.pitcher_stats["stuff"],
        "control": pitcher.character.pitcher_stats["control"],
        "batter_name": batter.character.name,
        "contact": batter.character.batter_stats["contact"],
        "power": batter.character.batter_stats["power"],
        "speed": batter.character.batter_stats["speed"],
        "strategy": strategy
    })
    
    return {"pitcher_decision": decision}

def batter_node(state: SimState):
    """타자 의사결정"""
    game = state["game"]
    pitcher = game.get_current_pitcher()
    batter = game.get_current_batter()
    
    strategy = state["away_manager_decision"].offense_strategy if game.half == Half.TOP else state["home_manager_decision"].offense_strategy
    
    prompt = ChatPromptTemplate.from_template(BATTER_PROMPT)
    chain = prompt | llm.with_structured_output(BatterDecision)
    
    decision = chain.invoke({
        "name": batter.character.name,
        "contact": batter.character.batter_stats["contact"],
        "power": batter.character.batter_stats["power"],
        "speed": batter.character.batter_stats["speed"],
        "pitcher_name": pitcher.character.name,
        "velocity": pitcher.character.pitcher_stats["velocity"],
        "stuff": pitcher.character.pitcher_stats["stuff"],
        "control": pitcher.character.pitcher_stats["control"],
        "strategy": strategy
    })
    
    return {"batter_decision": decision}

def resolver_node(state: SimState):
    """최종 결과 판정 (물리 엔진 역할)"""
    import traceback
    try:
        game = state["game"]
        pitcher = game.get_current_pitcher()
        batter = game.get_current_batter()
        
        ctx = state["director_ctx"]
        p_dec = state["pitcher_decision"]
        b_dec = state["batter_decision"]
        
        prompt = ChatPromptTemplate.from_template(RESOLVER_PROMPT)
        chain = prompt | llm.with_structured_output(SimulationResult)
        
        runners = {
            "runner_1": game.bases.basec1.character.name if game.bases.basec1 else "없음",
            "runner_2": game.bases.basec2.character.name if game.bases.basec2 else "없음",
            "runner_3": game.bases.basec3.character.name if game.bases.basec3 else "없음"
        }
        
        defense_team = game.get_defense_team()
        defense_info_lines = []
        for p in defense_team.roster:
            if p.character.role == Role.BATTER:
                d_stats = p.character.batter_stats.get("defense", {"range":50, "error":50, "arm":50})
                info = f"- {p.character.position_main} {p.character.name}: 범위 {d_stats['range']}, 실책 {d_stats['error']}, 어깨 {d_stats['arm']}"
                defense_info_lines.append(info)
        defense_lineup_str = "\n".join(defense_info_lines)
    
        val_res = state.get("validator_result")
        feedback = ""
        if val_res and not val_res.is_valid:
            feedback = f"⚠️ [PREVIOUS FAILED]: {val_res.error_type} - {val_res.correction_suggestion}"
        
        runners_status = f"주자: 1루[{runners['runner_1']}], 2루[{runners['runner_2']}], 3루[{runners['runner_3']}]"
        
        # Build Game Info Context with STRICT RULES
        score_diff = abs(game.home_score - game.away_score)
        game_info_lines = [
            f"- Inning: {game.inning} {game.half}",
            f"- Score: Home {game.home_score} : Away {game.away_score}",
            f"- Outs: {game.outs}",
            f"- Runners: {runners_status}"
        ]
        
        # Forced Rubber Banding
        if game.inning >= 7 and game.home_score == 0 and game.away_score == 0:
             game_info_lines.append("\n!!! NOTICE: 7이닝 이상 0-0입니다. [투수들의 집중력이 조금씩 떨어질 시점입니다]. !!!")
        elif game.inning >= 10 and score_diff == 0:
             game_info_lines.append("\n!!! NOTICE: 연장전 동점 상황입니다. [승부를 가를 수 있는 변수를 고려하세요]. !!!")

        game_info_str = "\n".join(game_info_lines)

        res = chain.invoke({
            "game_info": game_info_str,
            "weather": ctx.weather,
            "wind": ctx.wind_direction,
            "zone": ctx.umpire_zone,
            "outs": game.outs, # Redundant but kept for safety
            "runners_status": runners_status,
            "defense_lineup": defense_lineup_str,
            "pitcher_name": pitcher.character.name,
            "pitch_type": p_dec.pitch_type,
            "pitch_location": p_dec.location,
            "velocity": pitcher.character.pitcher_stats["velocity"],
            "stuff": pitcher.character.pitcher_stats["stuff"],
            "control": pitcher.character.pitcher_stats["control"],
            "mental": pitcher.character.pitcher_stats.get("mental", 50),
            "batter_name": batter.character.name,
            "aim_type": b_dec.aim_pitch_type,
            "aim_location": b_dec.aim_location,
            "contact": batter.character.batter_stats["contact"],
            "power": batter.character.batter_stats["power"],
            "speed": batter.character.batter_stats["speed"],
            "eye": batter.character.batter_stats.get("eye", 50),
            "clutch": batter.character.batter_stats.get("clutch", 50),
            "validator_feedback": feedback
        })
        
        return {"last_result": res}
    except Exception as e:
        err_msg = traceback.format_exc()
        with open("error_log.txt", "w", encoding="utf-8") as f:
            f.write(err_msg)
        print(f"Error in resolver_node: {e}")
        raise e

def validator_node(state: SimState):
    """시뮬레이션 결과 검증 (Rule Expert)"""
    try:
        game = state["game"]
        res = state["last_result"]
        
        prompt = ChatPromptTemplate.from_template(VALIDATOR_PROMPT)
        validator_chain = prompt | llm.with_structured_output(ValidatorResult)
        
        prev_runners = []
        if game.bases.basec1: prev_runners.append("1루")
        if game.bases.basec2: prev_runners.append("2루")
        if game.bases.basec3: prev_runners.append("3루")
        prev_runners_str = ",".join(prev_runners) if prev_runners else "없음"
        
        val_res = validator_chain.invoke({
            "outs": game.outs,
            "runners_before": prev_runners_str,
            "result_code": res.result_code,
            "description": res.description
        })
        
        current_retry = state.get("retry_count", 0)
        
        if not val_res.is_valid:
            if current_retry < 3:
                warn_msg = f"⚠️ [Validation Warning] {val_res.error_type}: {val_res.reasoning}. Retrying... ({current_retry+1}/3)"
                print(warn_msg)
                with open("simulation_log.txt", "a", encoding="utf-8") as f:
                    f.write(warn_msg + "\n")
                return {"validator_result": val_res, "retry_count": current_retry + 1}
            else:
                err_msg = f"❌ [Validation Failed] Max Retries Reached. Proceeding anyway. ({val_res.reasoning})"
                print(err_msg)
                with open("simulation_log.txt", "a", encoding="utf-8") as f:
                    f.write(err_msg + "\n")
                return {"validator_result": val_res, "retry_count": 0}
        else:
            return {"validator_result": val_res, "retry_count": 0}
        
    except Exception as e:
        print(f"Error in validator_node: {e}")
        return {"validator_result": None}

def update_state_node(state: SimState):
    """상태 업데이트 및 준비 (Agent-Environment Pattern)"""
    import traceback
    try:
        game = state["game"]
        res = state["last_result"]
        if not res:
            print("Error: last_result is None")
            return {"game": game}
        
        # [Data Integrity] Store the result
        game.last_result = res
        
        # --- [Agent-Environment Transition] ---
        # Agent has spoken (res.result_code). Now Environment reacts.
        # Use Deterministic Rule Engine
        runs_scored = BaseballRuleEngine.apply_result(game, res)
        
        # Log (Console)
        log_entry = f"[{game.inning}회{'초' if game.half==Half.TOP else '말'}] {res.description}"
        
        # 주자/점수 상황 로깅
        runners_log = []
        if game.bases.basec1: runners_log.append("1루: " + game.bases.basec1.character.name)
        if game.bases.basec2: runners_log.append("2루: " + game.bases.basec2.character.name)
        if game.bases.basec3: runners_log.append("3루: " + game.bases.basec3.character.name)
        runners_str = ", ".join(runners_log) if runners_log else "없음"
        
        log_entry += f" (주자: {runners_str}, 득점: {runs_scored})"
        game.logs.append(log_entry)
        
        # --- Data Logging (File) ---
        p_dec = state.get('pitcher_decision')
        b_dec = state.get('batter_decision')
        
        with open("simulation_log.txt", "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
            if p_dec and b_dec:
                f.write(f"   (P: {p_dec.pitch_type}/{p_dec.location}, B: {b_dec.style})\n")
    
        # 2. JSON Data Log (Frontend Interface)
        pitcher = game.get_current_pitcher()
        batter = game.get_current_batter()
        next_batter_info = game.get_next_batter_info()
        
        # Runners Info for Broadcast
        runners_data = [None, None, None]
        if game.bases.basec1: runners_data[0] = {"name": game.bases.basec1.character.name}
        if game.bases.basec2: runners_data[1] = {"name": game.bases.basec2.character.name}
        if game.bases.basec3: runners_data[2] = {"name": game.bases.basec3.character.name}
    
        broadcast_data = BroadcastData(
            match_id=game.match_id,
            inning=game.inning,
            half="TOP" if game.half == Half.TOP else "BOTTOM",
            outs=game.outs,
            home_score=game.home_score,
            away_score=game.away_score,
            current_batter={
                "name": batter.character.name,
                "role": "BATTER",
                "stats": batter.character.batter_stats
            },
            current_pitcher={
                "name": pitcher.character.name,
                "role": "PITCHER",
                "stats": pitcher.character.pitcher_stats
            },
            runners=runners_data,
            result=res,
            next_batter=next_batter_info
        )
        
        with open("broadcast_data.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(broadcast_data.model_dump(), ensure_ascii=False) + "\n")
    
        # Console Output (Broadcast)
        print(f"BROADCAST: {log_entry}")
        if p_dec and b_dec:
            print(f"   -> Pitcher: {p_dec.pitch_type} ({p_dec.effort})")
            print(f"   -> Batter: {b_dec.style} (Aim: {b_dec.aim_pitch_type})")
        
        # Prepare Next Batter
        game.next_batter()
        
        # --- Pitcher Mechanics & Substitution ---
        current_pitcher = game.get_current_pitcher()
        if current_pitcher and p_dec:
            current_pitcher.pitch_count += 1
            stamina_cost = 1
            if p_dec.effort == "Full_Power":
                stamina_cost = 3
            current_pitcher.current_stamina = max(0, current_pitcher.current_stamina - stamina_cost)
            
        defense_manager_dec = state["home_manager_decision"] if game.half == Half.TOP else state["away_manager_decision"]
        
        if defense_manager_dec.change_pitcher:
            try:
                defense_team = game.get_defense_team()
                old_pitcher_name = current_pitcher.character.name
                if defense_team.change_pitcher():
                    new_pitcher = defense_team.get_pitcher()
                    sub_log = f"🔄 [투수 교체] {defense_team.name}: {old_pitcher_name} -> {new_pitcher.character.name} (투구수: {current_pitcher.pitch_count}, 체력: {current_pitcher.current_stamina})"
                    game.logs.append(sub_log)
                    print(sub_log)
                    with open("simulation_log.txt", "a", encoding="utf-8") as f:
                        f.write(sub_log + "\n")
            except Exception as e:
                print(f"Substitution Error: {e}")
    
        return {"game": game}
    except Exception as e:
        err_msg = traceback.format_exc()
        with open("error_log.txt", "w", encoding="utf-8") as f:
            f.write(err_msg)
        print(f"Error in update_state_node: {e}")
        raise e

def check_inning_node(state: SimState):
    """이닝/경기 종료 조건 체크"""
    import traceback
    try:
        game = state["game"]
        
        if game.outs >= 3:
            game.outs = 0
            game.bases.basec1 = None
            game.bases.basec2 = None
            game.bases.basec3 = None
            
            if game.half == Half.TOP:
                game.half = Half.BOTTOM
            else:
                game.half = Half.TOP
                game.inning += 1
                
        # Game Over Condition (9이닝 이상 & 말 공격 종료 후 승부 남)
        if game.inning > 9:
             if game.half == Half.TOP: # 말 종료 직후 inning이 올라가서 TOP이 됨
                 # 이전 이닝(9회말, 10회말 등) 종료 시점의 점수 확인
                 if game.home_score != game.away_score:
                     game.status = SimulationStatus.FINISHED
                     return {"game": game}
        
        return {"game": game}
    except Exception as e:
        err_msg = traceback.format_exc()
        with open("error_log.txt", "w", encoding="utf-8") as f:
            f.write(err_msg)
        print(f"Error in check_inning_node: {e}")
        raise e

def check_game_end_condition(state: SimState):
    if state["game"].status == SimulationStatus.FINISHED:
        return "end"
    return "continue"

def route_validator(state: SimState):
    """검증 결과에 따른 라우팅"""
    val_res = state.get("validator_result")
    retry_count = state.get("retry_count", 0)
    
    if val_res and not val_res.is_valid and retry_count > 0:
        return "retry"
    return "continue"

# --- Graph Construction ---
workflow = StateGraph(SimState)

# Add Nodes
workflow.add_node("director", director_node)
workflow.add_node("manager", manager_node)
workflow.add_node("pitcher", pitcher_node)
workflow.add_node("batter", batter_node)
workflow.add_node("resolver", resolver_node)
workflow.add_node("validator", validator_node)
workflow.add_node("update_state", update_state_node)
workflow.add_node("check_inning", check_inning_node)

# Add Edges (Linear Pipeline)
workflow.set_entry_point("director")
workflow.add_edge("director", "manager")
workflow.add_edge("manager", "pitcher")
workflow.add_edge("pitcher", "batter")
workflow.add_edge("batter", "resolver")
workflow.add_edge("resolver", "validator")
workflow.add_conditional_edges(
    "validator",
    route_validator,
    {
        "retry": "resolver",
        "continue": "update_state"
    }
)
workflow.add_edge("update_state", "check_inning")
workflow.add_conditional_edges(
    "check_inning",
    check_game_end_condition,
    {
        "continue": "director",
        "end": END
    }
)

app = workflow.compile()


# --- Execution Entry ---
def run_engine(
    game_state: GameState, 
    db_session: Optional[Any] = None,
    on_step_callback=None
) -> GameState:
    """
    API에서 호출 가능한 시뮬레이션 엔진 진입점.
    """
    print(f"--- Engine Triggered for Match {game_state.match_id} ---")
    
    with open("simulation_log.txt", "a", encoding="utf-8") as f:
        f.write(f"\n\n=== New Match (ID: {game_state.match_id}) Triggered at {os.environ.get('HOSTNAME', 'Local')} ===\n")

    
    # Initialize Contexts
    director_ctx = DirectorContext()
    home_manager_decision = ManagerDecision(description="초기화", offense_strategy=TeamStrategy.NORMAL, defense_strategy=TeamStrategy.NORMAL)
    away_manager_decision = ManagerDecision(description="초기화", offense_strategy=TeamStrategy.NORMAL, defense_strategy=TeamStrategy.NORMAL)

    initial_state = {
        "game": game_state, 
        "db_session": db_session,
        "director_ctx": director_ctx,
        "home_manager_decision": home_manager_decision,
        "away_manager_decision": away_manager_decision,
        "pitcher_decision": PitcherDecision(pitch_type=PitchType.FASTBALL, location=PitchLocation.MIDDLE, description="Initial"),
        "batter_decision": BatterDecision(style=BattingStyle.CAUTIOUS, description="Initial"),
        "last_result": None,
        "validator_result": None,
        "retry_count": 0
    }
    
    # Run Graph
    step_count = 0
    for s in app.stream(initial_state, config={"recursion_limit": 3000}):
        if "update_state" in s:
            updated_game = s["update_state"]["game"]
            if on_step_callback:
                on_step_callback(updated_game)
            step_count += 1
            
    print(f"--- Simulation Finished (Steps: {step_count}) ---")
    print(f"Final Score: {game_state.away_team.name} {game_state.away_score} : {game_state.home_score} {game_state.home_team.name}")
    return game_state
