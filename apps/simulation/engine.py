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
from .models import GameState, SimulationResult, Half, SimulationStatus, BroadcastData
from .dummy_generator import init_dummy_game

# Load Env
load_dotenv()

# --- LLM Setup ---
llm = ChatOpenAI(model="gpt-4o", temperature=0.7)

# --- State for Graph ---
# We can use GameState as the graph state directly, but keeping it wrapped is safer for extension
class SimState(TypedDict):
    game: GameState
    last_result: SimulationResult | None

# --- Prompt Templates ---
AT_BAT_PROMPT = """
당신은 전문적인 야구 경기 시뮬레이터이자 중계 캐스터입니다.
현재 투수와 타자의 능력치, 그리고 경기 상황을 바탕으로 타석 결과를 시뮬레이션하고 생생한 중계를 하세요.

[투수 정보]
- 이름: {pitcher_name}
- 통계: 구속 {velocity}, 구위 {stuff}, 제구 {control}

[타자 정보]
- 이름: {batter_name}
- 통계: 컨택 {contact}, 파워 {power}, 스피드 {speed}

[경기 상황]
- {inning}회 {half}
- 점수: {away_team} {away_score} vs {home_team} {home_score}
- 주자: {runners}
- 아웃: {outs} OUT

[시뮬레이션 규칙]
1. 투수의 구위/구속이 타자의 컨택/파워보다 압도적이면 삼진이나 범타 확률이 높습니다.
2. 타자의 컨택이 높으면 안타 확률이 높고, 파워가 높으면 장타 확률이 높습니다.
3. 무승부는 없습니다. 끝장 승부입니다.
4. 결과 코드는 다음 중 하나여야 합니다: HIT_SINGLE, HIT_DOUBLE, HIT_TRIPLE, HOMERUN, WALK, STRIKEOUT, OUT_FLY, OUT_GROUND, OUT_LINE
5. `runs_scored`는 이 타석으로 인해 들어온 점수 합계입니다.
6. `runners_advanced`는 주자가 진루했는지 여부입니다.

결과를 JSON 형식으로 출력하세요.
"""

# --- Nodes ---

def at_bat_node(state: SimState):
    game = state["game"]
    pitcher = game.get_current_pitcher()
    batter = game.get_current_batter()

    # Runners String
    runners = []
    if game.bases.basec1: runners.append("1루")
    if game.bases.basec2: runners.append("2루")
    if game.bases.basec3: runners.append("3루")
    runners_str = ", ".join(runners) if runners else "없음"

    prompt = ChatPromptTemplate.from_template(AT_BAT_PROMPT)
    chain = prompt | llm.with_structured_output(SimulationResult)

    res: SimulationResult = chain.invoke({
        "pitcher_name": pitcher.character.name,
        "velocity": pitcher.character.pitcher_stats["velocity"],
        "stuff": pitcher.character.pitcher_stats["stuff"],
        "control": pitcher.character.pitcher_stats["control"],
        "batter_name": batter.character.name,
        "contact": batter.character.batter_stats["contact"],
        "power": batter.character.batter_stats["power"],
        "speed": batter.character.batter_stats["speed"],
        "inning": game.inning,
        "half": "초(TOP)" if game.half == Half.TOP else "말(BOTTOM)",
        "away_team": game.away_team.name,
        "home_team": game.home_team.name,
        "away_score": game.away_score,
        "home_score": game.home_score,
        "runners": runners_str,
        "outs": game.outs
    })

    return {"last_result": res}

def update_state_node(state: SimState):
    game = state["game"]
    res = state["last_result"]
    code = res.result_code

    # --- Score & Runners Logic (Simplified) ---
    # 실제로는 베이스별 주자 이동을 정교하게 다뤄야 하지만, 
    # 여기서는 결과 코드에 따라 단순화하여 처리함.
    
    scored = 0
    
    if "HIT" in code or code == "HOMERUN" or code == "WALK":
        # 타자 출루 처리 (간략화)
        # TODO: 실제로는 1루타, 2루타 등에 따라 주자 이동 로직 분기 필요
        pass 
        # (복잡한 야구 룰 로직은 LLM이 runs_scored를 줬다고 가정하고 스코어만 반영하거나,
        #  추후 정밀 구현. 여기서는 일단 LLM이 계산해준 점수만 반영하고 주자는 랜덤성으로 처리)
    
    # Update Stats
    if "OUT" in code or code == "STRIKEOUT":
        game.outs += 1
    
    # Score Update (LLM이 계산해준 점수 신뢰)
    if game.half == Half.TOP:
        game.away_score += res.runs_scored
    else:
        game.home_score += res.runs_scored

    # Log
    log_entry = f"[{game.inning}회{'초' if game.half==Half.TOP else '말'}] {res.description}"
    game.logs.append(log_entry)
    print(f"BROADCAST: {log_entry} (Next: {game.get_next_batter_info()['name']})")
    
    # Prepare Next Batter
    game.next_batter()

    return {"game": game}

def check_inning_node(state: SimState):
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
            
    # Game Over Condition (9이닝 이상 & 점수차 존재 & 말 공격 종료 or 초 공격 종료 후 홈팀 리드)
    # 간단하게 9회말 종료 후 동점이 아니면 종료
    if game.inning > 9:
        if game.home_score != game.away_score:
            if game.half == Half.TOP and game.home_score > game.away_score:
                 # 10회초 종료인데 홈팀이 이기고 있으면 종료? (사실 9회말 끝났을때 체크해야함)
                 # 로직 단순화: 말이 끝났을 때 동점이 아니면 종료
                 pass
            
            # 말이 끝난 직후 체크
            if game.half == Half.TOP: # 방금 말이 끝나고 초가 된 상태 (inning 증가됨)
                 # 이전 이닝 말 종료 시점 체크
                 if game.home_score != game.away_score:
                     game.status = SimulationStatus.FINISHED
                     return {"game": game}

    return {"game": game}

def check_game_end_condition(state: SimState):
    game = state["game"]
    if game.status == SimulationStatus.FINISHED:
        return "end"
    return "continue"

# --- Graph Construction ---
workflow = StateGraph(SimState)

workflow.add_node("at_bat", at_bat_node)
workflow.add_node("update_state", update_state_node)
workflow.add_node("check_inning", check_inning_node)

workflow.set_entry_point("at_bat")

workflow.add_edge("at_bat", "update_state")
workflow.add_edge("update_state", "check_inning")

workflow.add_conditional_edges(
    "check_inning",
    check_game_end_condition,
    {
        "continue": "at_bat",
        "end": END
    }
)

app = workflow.compile()

# --- Execution Entry ---
def run_simulation():
    print("--- Simulation Start ---")
    game = init_dummy_game()
    initial_state = {"game": game, "last_result": None}
    
    # Run Graph
    # 야구 경기는 타석 수가 많으므로 recursion_limit을 충분히 늘려줍니다.
    for s in app.stream(initial_state, config={"recursion_limit": 1000}):
        pass # Stream으로 진행 상황 볼 수 있음
        
    print(f"--- Simulation Finished ---")
    print(f"Final Score: {game.away_team.name} {game.away_score} : {game.home_score} {game.home_team.name}")
    print("Logs:")
    for l in game.logs[-5:]: # Last 5 logs
        print(l)

if __name__ == "__main__":
    run_simulation()
