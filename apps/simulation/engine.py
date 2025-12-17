import os
import random
import json
from typing import TypedDict, Annotated, List, Dict
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
    PitchType, PitchLocation, BattingStyle
)
from .dummy_generator import init_dummy_game

# Load Env
load_dotenv()

# --- LLM Setup ---
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

# --- State for Graph ---
class SimState(TypedDict):
    game: GameState
    # Decisions (Mental State)
    director_ctx: DirectorContext
    home_manager_decision: ManagerDecision
    away_manager_decision: ManagerDecision
    pitcher_decision: PitcherDecision
    batter_decision: BatterDecision
    # Result
    last_result: SimulationResult | None

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

[가능한 작전]
- NORMAL: 정상 플레이
- BUNT: 번트 시도 (주자가 있을 때, 접전 상황)
- HIT_AND_RUN: 히트 앤드 런 (주자가 빠르고 타자가 컨택이 좋을 때)
- INFIELD_IN: 전진 수비 (3루 주자 실점을 막아야 할 때)
- LONG_BALL: 장타 노림 (점수 차가 클 때, 파워 히터)

당신의 작전과 그 이유를 설명하세요.
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
당신은 야구 매치의 결과를 판정하는 심판이자 물리 엔진입니다.
모든 변수(능력치, 날씨, 작전, 투수 의도, 타자 의도)와 **현재 주자 상황**을 종합해 타석 결과와 **최종 주자 위치**를 판정하세요.

[환경]
- 날씨: {weather}, 바람: {wind}, 심판 존: {zone}

[현재 주자 상황]
- 1루: {runner_1}
- 2루: {runner_2}
- 3루: {runner_3}

[투수 {pitcher_name}]
- 의도: {pitch_type} ({pitch_location})
- 능력: 구속 {velocity}, 구위 {stuff}, 제구 {control}
- (제구가 낮으면 실투 가능성 있음)

[타자 {batter_name}]
- 의도: 노림수 {aim_type}, 코스 {aim_location}, 스타일 {style}
- 능력: 컨택 {contact}, 파워 {power}, 스피드 {speed}

[감독 작전]
- 수비측: {def_strategy}
- 공격측: {off_strategy}

[판정 로직 (Rules-Free)]
1. 투수와 타자의 대결 결과를 물리적으로 추론하세요.
2. 결과에 따라 **주자들이 어디까지 진루했을지** 판단하세요.
   - 예: "우중간 깊은 타구! 1루 주자는 발이 빠르니 3루까지 달립니다."
   - 예: "내야 땅볼! 1루 주자는 2루에서 아웃, 타자는 1루 세이프."
   - 예: "홈런! 모든 주자와 타자가 득점합니다."
   - 예: "볼넷! 밀어내기 상황이거나 1루가 비어있으면 채웁니다."
3. 득점도 직접 계산하세요.

결과를 JSON으로 출력하세요.
- `reasoning`: 타구의 질, 수비 위치, 주자 속도 등을 고려한 판정 이유
- `result_code`: (1B, 2B, 3B, HR, BB, SO, FO, GO, HBP, ERROR)
    - 1B=1루타, 2B=2루타, 3B=3루타, HR=홈런
    - BB=볼넷, SO=삼진, HBP=사구
    - FO=뜬공아웃, GO=땅볼아웃, ERROR=실책
- `description`: 생생한 중계 멘트 (투수 vs 타자 및 주자 플레이 묘사)
- `final_bases`: **[1루주자, 2루주자, 3루주자]** 리스트. (인덱스 주의)
    - **Index 0 = 1루 (1st Base)**
    - **Index 1 = 2루 (2nd Base)**
    - **Index 2 = 3루 (3rd Base)**
    - 예: 주자 없을 때 1루타 -> `["타자이름", null, null]` (0번 인덱스 채움)
    - 예: 주자 없을 때 2루타 -> `[null, "타자이름", null]` (1번 인덱스 채움)
    - 예: 1루 주자("A")가 있고 타자("B")가 안타 -> `["B", "A", null]` (B는 1루, A는 2루로 이동)
    - **주의**: 주자는 서로 추월할 수 없습니다. 1루 주자가 3루에 가려면 2루 주자는 홈으로 들어와야(득점) 합니다.
- `runs_scored`: 이 플레이로 들어온 득점 수 (점수 계산 필수)
"""

# --- Nodes ---

def director_node(state: SimState):
    """경기 환경 설정"""
    game = state["game"]
    ctx = state.get("director_ctx", DirectorContext())
    
    # 이닝 초반이거나 특정 상황에서만 환경 변화 (API 호출 절약 위해 간단한 로직 적용 가능)
    # 여기서는 매 타석 체크한다고 가정 (환경이 급변하진 않으므로 temperature 0.3)
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
    """양 팀 감독의 작전 지시 (병렬 처리 가능하지만 순차 처리함)"""
    game = state["game"]
    
    # Home Manager
    prompt = ChatPromptTemplate.from_template(MANAGER_PROMPT)
    manager_chain = prompt | llm.with_structured_output(ManagerDecision)
    
    runners = []
    if game.bases.basec1: runners.append("1루")
    if game.bases.basec2: runners.append("2루")
    runners_str = ",".join(runners) if runners else "없음"
    
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
        "opponent_name": game.get_current_pitcher().character.name
    })

    # Away Manager
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
        "opponent_name": game.get_current_pitcher().character.name
    })

    return {
        "home_manager_decision": home_decision,
        "away_manager_decision": away_decision
    }

def pitcher_node(state: SimState):
    """투수 의사결정"""
    game = state["game"]
    pitcher = game.get_current_pitcher()
    batter = game.get_current_batter()
    
    # 수비팀 감독의 작전 확인
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
    
    # 공격팀 감독의 작전 확인
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
    game = state["game"]
    pitcher = game.get_current_pitcher()
    batter = game.get_current_batter()
    
    ctx = state["director_ctx"]
    p_dec = state["pitcher_decision"]
    b_dec = state["batter_decision"]
    
    def_strategy = state["home_manager_decision"].defense_strategy if game.half == Half.TOP else state["away_manager_decision"].defense_strategy
    off_strategy = state["away_manager_decision"].offense_strategy if game.half == Half.TOP else state["home_manager_decision"].offense_strategy
    
    prompt = ChatPromptTemplate.from_template(RESOLVER_PROMPT)
    chain = prompt | llm.with_structured_output(SimulationResult)
    
    runners = {
        "runner_1": game.bases.basec1.character.name if game.bases.basec1 else "없음",
        "runner_2": game.bases.basec2.character.name if game.bases.basec2 else "없음",
        "runner_3": game.bases.basec3.character.name if game.bases.basec3 else "없음"
    }

    res = chain.invoke({
        "weather": ctx.weather,
        "wind": ctx.wind_direction,
        "zone": ctx.umpire_zone,
        "runner_1": runners["runner_1"],
        "runner_2": runners["runner_2"],
        "runner_3": runners["runner_3"],
        "pitcher_name": pitcher.character.name,
        "pitch_type": p_dec.pitch_type,
        "pitch_location": p_dec.location,
        "velocity": pitcher.character.pitcher_stats["velocity"],
        "stuff": pitcher.character.pitcher_stats["stuff"],
        "control": pitcher.character.pitcher_stats["control"],
        "batter_name": batter.character.name,
        "aim_type": b_dec.aim_pitch_type,
        "aim_location": b_dec.aim_location,
        "style": b_dec.style,
        "contact": batter.character.batter_stats["contact"],
        "power": batter.character.batter_stats["power"],
        "speed": batter.character.batter_stats["speed"],
        "def_strategy": def_strategy,
        "off_strategy": off_strategy
    })
    
    return {"last_result": res}

def update_state_node(state: SimState):
    """상태 업데이트 및 준비"""
    game = state["game"]
    res = state["last_result"]
    code = res.result_code
    
    batter = game.get_current_batter()

    # --- Score Logic based on LLM ---
    # LLM이 runs_scored를 직접 계산해서 줌
    runs_scored = res.runs_scored
    
    # 득점 반영
    if game.half == Half.TOP:
        game.away_score += runs_scored
    else:
        game.home_score += runs_scored
        
    if code in [ResultCode.SO, ResultCode.FO, ResultCode.GO]:
        game.outs += 1

    # --- Base Update (Mapping LLM names to Objects) ---
    # LLM returns names: ["Kim", "Lee", None]
    # We need to find player objects from current lineups or runners
    
    # 현재 필드에 있는 주자들 + 타자 후보군
    potential_runners = [game.bases.basec1, game.bases.basec2, game.bases.basec3, batter]
    potential_runners = [r for r in potential_runners if r is not None]
    
    # 이름으로 매핑 (동명이인 처리 안됨 - 일단 이름 유니크 가정)
    player_map = {p.character.name: p for p in potential_runners}
    
    new_bases_objs = [None, None, None]
    
    for i, r_name in enumerate(res.final_bases):
        if r_name and r_name in player_map:
            new_bases_objs[i] = player_map[r_name]
        elif r_name and r_name == batter.character.name: # 타자가 나갔을 경우
            new_bases_objs[i] = batter
            
    game.bases.basec1 = new_bases_objs[0]
    game.bases.basec2 = new_bases_objs[1]
    game.bases.basec3 = new_bases_objs[2]

    # Log (Console)
    log_entry = f"[{game.inning}회{'초' if game.half==Half.TOP else '말'}] {res.description}"
    # 주자/점수 상황 추가 로깅
    runners_log = []
    if game.bases.basec1: runners_log.append("1루")
    if game.bases.basec2: runners_log.append("2루")
    if game.bases.basec3: runners_log.append("3루")
    runners_str = ",".join(runners_log) if runners_log else "없음"
    
    log_entry += f" (주자: {runners_str}, 득점: {runs_scored})"
    game.logs.append(log_entry)
    
    # --- Data Logging (File) ---
    # 1. Text Log
    with open("simulation_log.txt", "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")
        f.write(f"   (P: {state['pitcher_decision'].pitch_type}/{state['pitcher_decision'].location}, B: {state['batter_decision'].style})\n")

    # 2. JSON Data Log (Frontend Interface)
    # create BroadcastData
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
    print(f"   -> Pitcher: {state['pitcher_decision'].pitch_type} ({state['pitcher_decision'].effort})")
    print(f"   -> Batter: {state['batter_decision'].style} (Aim: {state['batter_decision'].aim_pitch_type})")
    
    # Prepare Next Batter
    game.next_batter()

    return {"game": game}

def check_inning_node(state: SimState):
    """이닝/경기 종료 조건 체크"""
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

def check_game_end_condition(state: SimState):
    if state["game"].status == SimulationStatus.FINISHED:
        return "end"
    return "continue"

# --- Graph Construction ---
workflow = StateGraph(SimState)

# Add Nodes
workflow.add_node("director", director_node)
workflow.add_node("manager", manager_node)
workflow.add_node("pitcher", pitcher_node)
workflow.add_node("batter", batter_node)
workflow.add_node("resolver", resolver_node)
workflow.add_node("update_state", update_state_node)
workflow.add_node("check_inning", check_inning_node)

# Add Edges (Linear Pipeline)
workflow.set_entry_point("director")
workflow.add_edge("director", "manager")
workflow.add_edge("manager", "pitcher")
workflow.add_edge("pitcher", "batter")
workflow.add_edge("batter", "resolver")
workflow.add_edge("resolver", "update_state")
workflow.add_edge("update_state", "check_inning")

workflow.add_conditional_edges(
    "check_inning",
    check_game_end_condition,
    {
        "continue": "director", # 다음 타석 시작 시 다시 환경부터 체크 (혹은 manager부터 해도 됨)
        "end": END
    }
)

app = workflow.compile()

# --- Execution Entry ---
# --- Execution Entry ---
def run_engine(
    initial_game_state: GameState, 
    director_ctx: DirectorContext = None,
    home_manager_decision: ManagerDecision = None,
    away_manager_decision: ManagerDecision = None,
    on_step_callback=None
):
    """
    API에서 호출 가능한 시뮬레이션 엔진 진입점.
    initial_game_state: DB에서 로드/변환된 초기 게임 상태
    on_step_callback: 매 스텝(타석)이 끝날 때마다 호출되는 콜백 함수 (DB 저장용) func(game_state: GameState)
    """
    print(f"--- Engine Triggered for Match {initial_game_state.match_id} ---")
    
    if director_ctx is None:
        director_ctx = DirectorContext()
    if home_manager_decision is None:
        home_manager_decision = ManagerDecision(description="초기화", offense_strategy=TeamStrategy.NORMAL, defense_strategy=TeamStrategy.NORMAL)
    if away_manager_decision is None:
        away_manager_decision = ManagerDecision(description="초기화", offense_strategy=TeamStrategy.NORMAL, defense_strategy=TeamStrategy.NORMAL)

    initial_state = {
        "game": initial_game_state, 
        "director_ctx": director_ctx,
        "home_manager_decision": home_manager_decision,
        "away_manager_decision": away_manager_decision,
        "pitcher_decision": PitcherDecision(pitch_type=PitchType.FASTBALL, location=PitchLocation.MIDDLE, description="Initial"),
        "batter_decision": BatterDecision(style=BattingStyle.CAUTIOUS, description="Initial"),
        "last_result": None
    }
    
    # Run Graph
    step_count = 0
    for s in app.stream(initial_state, config={"recursion_limit": 1000}):
        # s is a dict of updated state keys, e.g., {'update_state': {'game': ...}}
        
        # 'update_state' 노드가 실행된 직후에 DB 저장 등 콜백 호출
        if "update_state" in s:
            updated_game = s["update_state"]["game"]
            if on_step_callback:
                on_step_callback(updated_game)
            step_count += 1
            
    print(f"--- Simulation Finished (Steps: {step_count}) ---")
    print(f"Final Score: {initial_game_state.away_team.name} {initial_game_state.away_score} : {initial_game_state.home_score} {initial_game_state.home_team.name}")
    return initial_game_state

def run_simulation_cli():
    """Local CLI Test Entry"""
    print("--- Multi-Agent Engine Start (CLI) ---")
    # Clear Logs
    with open("simulation_log.txt", "w", encoding="utf-8") as f:
        f.write("=== Simulation Start ===\n")
    with open("broadcast_data.jsonl", "w", encoding="utf-8") as f:
        pass

    game = init_dummy_game()
    game = run_engine(game)

if __name__ == "__main__":
    run_simulation_cli()
