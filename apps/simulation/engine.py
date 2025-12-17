import os
import random
import json
from typing import TypedDict, Annotated, List, Dict, Optional
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
주어진 데이터(선수 능력, 상황, 작전)를 분석하여 **가장 현실적이고 개연성 있는 경기 결과**를 도출하세요.

**[중요] 추론 과정 (Chain of Thought)**
결과를 내기 전에 `reasoning` 필드에 다음 단계로 생각을 정리하세요.
1. **Matchup Analysis**: 투수의 구위/제구 vs 타자의 컨택/파워 비교. 누가 우위인가?
2. **Contact Quality**: 타구의 질(속도, 각도, 방향) 결정. 정타인가 빗맞았는가?
3. **Defense Check**: 타구 방향의 수비수 능력(범위, 어깨) 확인. 잡을 수 있는가?
4. **Base Running**: 안타/아웃 여부에 따른 주자들의 이동 판단. (무리한 주루 지양)
5. **Final Decision**: 최종 판정 코드 및 주자 위치 확정.

[가이드라인 (Scenario Tips)]
- **내야 땅볼(Ground ball)**:
  - 1루 주자는 2루로 가다가 아웃되거나(병살타), 2루에 안착합니다. 3루까지 가는 경우는 거의 없습니다.
  - 타자 주자는 발이 아주 빠르지 않으면 보통 1루에서 아웃입니다.
- **외야 안타(Single/Double)**:
  - 단타(Single): 2루 주자는 홈에 들어올 수도 3루에 멈출 수도 있습니다(외야수 어깨 고려). 1루 주자는 보통 2루, 빠르면 3루까지 갑니다.
  - 장타(Double/Triple): 주자들은 대부분 2~3 베이스를 진루합니다.
- **외야 뜬공(Fly ball)**:
  - 3루 주자는 태그업하여 득점할 수 있습니다(희생플라이).
  - 1루/2루 주자는 보통 움직이지 못합니다.
- **투수/타자 상성**:
  - 투수 체력이 낮으면(Stamina < 30) 제구 난조로 볼넷이나 장타 허용 확률이 급증합니다.
  - 타자의 노림수가 적중하면 안타 확률이 대폭 상승합니다.

[환경]
- 날씨: {weather}, 바람: {wind}, 심판 존: {zone}

[현재 주자 상황]
- 1루: {runner_1}
- 2루: {runner_2}
- 3루: {runner_3}

[수비 라인업 (Defenders)]
수비수 스탯 (범위: Range, 실책: Error, 어깨: Arm)
{defense_lineup}

[투수 {pitcher_name}]
- 의도: {pitch_type} ({pitch_location})
- 능력: 구속 {velocity}, 구위 {stuff}, 제구 {control}, 체력 {stamina}, 멘탈 {mental}

[타자 {batter_name}]
- 의도: 노림수 {aim_type}, 코스 {aim_location}, 스타일 {style}
- 능력: 컨택 {contact}, 파워 {power}, 스피드 {speed}, 선구안 {eye}, 클러치 {clutch}

[감독 작전]
- 수비측: {def_strategy}
- 공격측: {off_strategy}

위 정보를 종합하여 JSON 형식으로 응답하세요.
"""

VALIDATOR_PROMPT = """
당신은 **야구 규칙 전문가(Baseball Rule Expert)**이자 **데이터 검증관**입니다.
직전의 게임 상황과 시뮬레이션 결과(`SimulationResult`)를 비교하여 **논리적 오류**나 **규칙 위반**이 없는지 검증하세요.

[검증 기준 (Checklist)]
1. **Runner Consistency**: 주자가 순간이동하거나 역주행하지 않았는가? (예: 1루 주자가 갑자기 3루에 있거나 사라짐)
2. **Out Count Logic**: 아웃 종류(삼진, 땅볼 등)에 따라 아웃 카운트가 올바르게 처리될 상황인가?
3. **Score Logic**: 득점(runs_scored)이 발생했다면, 주자가 홈에 들어올 수 있는 타구였는가? (예: 내야 땅볼에 2루 주자 득점은 매우 드묾)
4. **Base Occupancy**: 한 루에 두 명의 주자가 있지 않은가?

[직전 상황]
- 아웃: {outs}, 주자: {runners_before}

[시뮬레이션 판정 결과]
- 결과: {result_code} ({description})
- 최종 주자: {final_bases}
- 득점: {runs_scored}

위 내용을 분석하여 정합성 여부(`is_valid`)와 그 이유(`reasoning`)를 판단하세요.
문제가 있다면 `error_type`과 `correction_suggestion`을 제시하세요.
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
    import traceback
    try:
        game = state["game"]
        
        # Home Manager
        prompt = ChatPromptTemplate.from_template(MANAGER_PROMPT)
        manager_chain = prompt | llm.with_structured_output(ManagerDecision)
        
        runners = []
        if game.bases.basec1: runners.append("1루")
        if game.bases.basec2: runners.append("2루")
        if game.bases.basec3: runners.append("3루") # Added missing 3rd base runner
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
            
            # Pitcher Info
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
            
            # Pitcher Info
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
    import traceback
    try:
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
        # --- 수비 라인업 정보 생성 ---
        defense_team = game.get_defense_team()
        defense_info_lines = []
        for p in defense_team.roster:
            if p.character.role == Role.BATTER:
                d_stats = p.character.batter_stats.get("defense", {"range":50, "error":50, "arm":50}) # 안전하게 get 사용
                info = f"- {p.character.position_main} {p.character.name}: 범위 {d_stats['range']}, 실책 {d_stats['error']}, 어깨 {d_stats['arm']}"
                defense_info_lines.append(info)
            elif p.character.role == Role.PITCHER and p.character.name == pitcher.character.name:
                 pass
        defense_lineup_str = "\n".join(defense_info_lines)
    
        res = chain.invoke({
            "weather": ctx.weather,
            "wind": ctx.wind_direction,
            "zone": ctx.umpire_zone,
            "runner_1": runners["runner_1"],
            "runner_2": runners["runner_2"],
            "runner_3": runners["runner_3"],
            "defense_lineup": defense_lineup_str,
            
            "pitcher_name": pitcher.character.name,
            "pitch_type": p_dec.pitch_type,
            "pitch_location": p_dec.location,
            "velocity": pitcher.character.pitcher_stats["velocity"],
            "stuff": pitcher.character.pitcher_stats["stuff"],
            "control": pitcher.character.pitcher_stats["control"],
            "stamina": pitcher.character.pitcher_stats.get("stamina", 100), # 안전하게 get 사용
            "mental": pitcher.character.pitcher_stats.get("mental", 50),
            
            "batter_name": batter.character.name,
            "aim_type": b_dec.aim_pitch_type,
            "aim_location": b_dec.aim_location,
            "style": b_dec.style,
            "contact": batter.character.batter_stats["contact"],
            "power": batter.character.batter_stats["power"],
            "speed": batter.character.batter_stats["speed"],
            "eye": batter.character.batter_stats.get("eye", 50),
            "clutch": batter.character.batter_stats.get("clutch", 50),
            
            "def_strategy": def_strategy,
            "off_strategy": off_strategy
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
        # Validator Chain (Using same LLM)
        validator_chain = prompt | llm.with_structured_output(ValidatorResult)
        
        # Previous Runners String
        prev_runners = []
        if game.bases.basec1: prev_runners.append("1루")
        if game.bases.basec2: prev_runners.append("2루")
        if game.bases.basec3: prev_runners.append("3루")
        prev_runners_str = ",".join(prev_runners) if prev_runners else "없음"
        
        val_res = validator_chain.invoke({
            "outs": game.outs,
            "runners_before": prev_runners_str,
            "result_code": res.result_code,
            "description": res.description,
            "final_bases": str(res.final_bases),
            "runs_scored": res.runs_scored
        })
        
        # Log Validation Result
        current_retry = state.get("retry_count", 0)
        
        if not val_res.is_valid:
            if current_retry < 3:
                warn_msg = f"⚠️ [Validation Warning] {val_res.error_type}: {val_res.reasoning}. Retrying... ({current_retry+1}/3)"
                print(warn_msg)
                with open("simulation_log.txt", "a", encoding="utf-8") as f:
                    f.write(warn_msg + "\n")
                # Retry logic: state update only, routing is handled by conditional edge
                return {"validator_result": val_res, "retry_count": current_retry + 1}
            else:
                err_msg = f"❌ [Validation Failed] Max Retries Reached. Proceeding anyway. ({val_res.reasoning})"
                print(err_msg)
                with open("simulation_log.txt", "a", encoding="utf-8") as f:
                    f.write(err_msg + "\n")
                return {"validator_result": val_res, "retry_count": 0} # Reset for next turn
        else:
            # print(f"✅ Validation Passed: {val_res.reasoning}")
            # Success -> Reset retry count
            return {"validator_result": val_res, "retry_count": 0}
        
    except Exception as e:
        print(f"Error in validator_node: {e}")
        # 검증 실패해도 게임은 진행 (일단 Pass)
        return {"validator_result": None}

def update_state_node(state: SimState):
    """상태 업데이트 및 준비"""
    import traceback
    try:
        game = state["game"]
        res = state["last_result"]
        if not res:
            print("Error: last_result is None")
            return {"game": game}
            
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
            
        if "OUT" in code or code == "STRIKEOUT":
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
        p_dec = state.get('pitcher_decision')
        b_dec = state.get('batter_decision')
        
        with open("simulation_log.txt", "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
            if p_dec and b_dec:
                f.write(f"   (P: {p_dec.pitch_type}/{p_dec.location}, B: {b_dec.style})\n")
    
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
        if p_dec and b_dec:
            print(f"   -> Pitcher: {p_dec.pitch_type} ({p_dec.effort})")
            print(f"   -> Batter: {b_dec.style} (Aim: {b_dec.aim_pitch_type})")
        
        # Prepare Next Batter
        game.next_batter()
        
        # --- [Phase 2] Pitcher Mechanics & Substitution ---
        # 1. Update Pitch Count & Stamina
        current_pitcher = game.get_current_pitcher()
        if current_pitcher and p_dec:
            current_pitcher.pitch_count += 1
            stamina_cost = 1 # [TEST] 체력 급격히 감소
            if p_dec.effort == "Full_Power":
                stamina_cost = 3
            current_pitcher.current_stamina = max(0, current_pitcher.current_stamina - stamina_cost)
            
        # 2. Substitution Check
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
    
    # 마지막 시도가 실패했고, 아직 재시도 횟수가 카운트된 상태라면(즉 리셋 안됨)
    # validator_node에서 이미 max check를 해서 0으로 리셋했으면 continue임.
    # validator_node에서 current_retry + 1을 리턴했으면 재시도임.
    
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
workflow.add_node("validator", validator_node) # Added Validator
workflow.add_node("update_state", update_state_node)
workflow.add_node("check_inning", check_inning_node)

# Add Edges (Linear Pipeline)
workflow.set_entry_point("director")
workflow.add_edge("director", "manager")
workflow.add_edge("manager", "pitcher")
workflow.add_edge("pitcher", "batter")
workflow.add_edge("batter", "resolver")
workflow.add_edge("resolver", "validator") # Resolver -> Validator
# validator -> update_state (Conditional)

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
        "continue": "director", # 다음 타석 시작 시 다시 환경부터 체크 (혹은 manager부터 해도 됨)
        "end": END
    }
)

app = workflow.compile()

# --- Execution Entry ---
def run_simulation():
    print("--- Multi-Agent Engine Start ---")
    
    # Clear Logs
    with open("simulation_log.txt", "w", encoding="utf-8") as f:
        f.write("=== Simulation Start ===\n")
    with open("broadcast_data.jsonl", "w", encoding="utf-8") as f:
        pass

    game = init_dummy_game()
    initial_state = {
        "game": game, 
        "director_ctx": DirectorContext(),
        "home_manager_decision": ManagerDecision(description="초기화", offense_strategy=TeamStrategy.NORMAL, defense_strategy=TeamStrategy.NORMAL),
        "away_manager_decision": ManagerDecision(description="초기화", offense_strategy=TeamStrategy.NORMAL, defense_strategy=TeamStrategy.NORMAL),
        "pitcher_decision": PitcherDecision(pitch_type=PitchType.FASTBALL, location=PitchLocation.MIDDLE, description="Initial"),
        "batter_decision": BatterDecision(style=BattingStyle.CAUTIOUS, description="Initial"),
        "last_result": None,
        "validator_result": None,
        "retry_count": 0
    }
    
    # Run Graph
    for s in app.stream(initial_state, config={"recursion_limit": 1000}):
        pass 
        
    print(f"--- Simulation Finished ---")
    print(f"Final Score: {game.away_team.name} {game.away_score} : {game.home_score} {game.home_team.name}")

if __name__ == "__main__":
    import traceback
    try:
        run_simulation()
    except Exception as e:
        err_msg = traceback.format_exc()
        with open("error_log.txt", "w", encoding="utf-8") as f:
            f.write(err_msg)
        print(f"CRITICAL ERROR in Main Loop: {e}")
