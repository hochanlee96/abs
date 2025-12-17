import os
import random
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
llm = ChatOpenAI(model="gpt-4o", temperature=0.7)

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
모든 변수(능력치, 날씨, 작전, 투수 의도, 타자 의도)를 종합해 타석 결과를 판정하세요.

[환경]
- 날씨: {weather}, 바람: {wind}, 심판 존: {zone}

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

[판정 로직]
1. 투수의 제구력과 의도에 따라 실제 투구가 결정됩니다.
2. 타자의 노림수가 적중하면 안타/장타 확률이 **대폭** 상승합니다.
3. 빗맞으면 땅볼/플라이 확률이 높습니다.
4. 날씨(비, 바람)가 수비 실책이나 타구 비거리에 영향을 줄 수 있습니다.
5. 무승부는 없습니다.

결과를 JSON으로 출력하세요. `result_code`는 (HIT_SINGLE, HIT_DOUBLE, HIT_TRIPLE, HOMERUN, WALK, STRIKEOUT, OUT_GROUND, OUT_FLY, OUT_LINE, ERROR) 중 하나여야 합니다.
중계 멘트(`description`)는 아주 생생하게, 투수와 타자의 수싸움 결과를 묘사하세요.
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
    
    res = chain.invoke({
        "weather": ctx.weather,
        "wind": ctx.wind_direction,
        "zone": ctx.umpire_zone,
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

    # --- Score Logic (Simplified) ---
    scored = 0
    # 타점/득점 처리는 LLM이 준 runs_scored를 믿음
    
    if game.half == Half.TOP:
        game.away_score += res.runs_scored
    else:
        game.home_score += res.runs_scored
        
    if "OUT" in code or code == "STRIKEOUT":
        game.outs += 1

    # Log
    log_entry = f"[{game.inning}회{'초' if game.half==Half.TOP else '말'}] {res.description}"
    game.logs.append(log_entry)
    
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
def run_simulation():
    print("--- Multi-Agent Engine Start ---")
    game = init_dummy_game()
    initial_state = {
        "game": game, 
        "director_ctx": DirectorContext(),
        "home_manager_decision": ManagerDecision(description="초기화", offense_strategy=TeamStrategy.NORMAL, defense_strategy=TeamStrategy.NORMAL),
        "away_manager_decision": ManagerDecision(description="초기화", offense_strategy=TeamStrategy.NORMAL, defense_strategy=TeamStrategy.NORMAL),
        "pitcher_decision": PitcherDecision(pitch_type=PitchType.FASTBALL, location=PitchLocation.MIDDLE, description="Initial"),
        "batter_decision": BatterDecision(style=BattingStyle.CAUTIOUS, description="Initial"),
        "last_result": None
    }
    
    # Run Graph
    for s in app.stream(initial_state, config={"recursion_limit": 1000}):
        pass 
        
    print(f"--- Simulation Finished ---")
    print(f"Final Score: {game.away_team.name} {game.away_score} : {game.home_score} {game.home_team.name}")

if __name__ == "__main__":
    run_simulation()
