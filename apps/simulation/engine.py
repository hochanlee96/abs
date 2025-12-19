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

**[중요] 생각의 사슬 (Chain of Thought) 필수**
결과를 내기 전에 `reasoning` 필드에 다음 단계로 생각을 정리하세요.
1.  **Matchup Analysis**: 투수의 구위/제구 vs 타자의 컨택/파워 비교. 누가 이겼는가?
    *   **[Game Balance]**: 야구의 **평균 타율은 0.250~0.280**입니다. 즉, 70%% 이상은 아웃되어야 합니다. 슈퍼스타도 3할대입니다. 타자에게 너무 후하지 않게 엄격히 판정하세요.
2.  **Contact Physics**: 타격이 이겼다면, 공이 어디로, 얼마나 빠르게, 어떤 각도로 날아갔는가?
3.  **Defense & Fielding**: 그 타구를 수비수가 잡을 수 있는가? (잡으면 아웃, 못 잡으면 안타)
4.  **Runner Advancement (매우 중요)**:
    *   **안타(1B/2B/3B)**: 타자는 **반드시** 주자가 되어 루상에 나가야 합니다. (예: 1루타면 타자 이름을 1루에 배치)
    *   **주자 밀어내기(Push)**: 1루에 주자가 있는데 1루타가 나오면, 1루 주자는 2루로 가야 합니다. 2루 주자는 3루 또는 홈으로, 3루 주자는 홈으로 들어옵니다.
    *   **타자 주자**: 타자도 주자 리스트에 포함되어야 함을 절대 잊지 마세요.
5.  **Validation Feedback Check**: 이전 피드백을 반드시 반영하여 수정하세요.

**[Output Format]**
*   `final_bases`: **반드시 3개의 요소**를 가진 리스트여야 합니다. `[1루주자이름, 2루주자이름, 3루주자이름]`.
    *   주자가 없으면 `null` (Python: `None`).
    *   예시: `["Kim Min-ji", null, "Lee Chul-su"]` (1루: 김민지, 2루: 없음, 3루: 이철수)
*   **주의**: 타자 이름 `{batter_name}`을 결과 리스트의 적절한 위치에 꼭 넣으세요 (안타/볼넷 시).

**[Few-shot Examples (정답 노트)]**
*   **Case 1 (단타 시 주자 이동 - 밀어내기)**
    *   상황: 주자 1루(Lee), 타자(Kim) 안타(우전 1루타)
    *   잘못된 결과: `final_bases`: `["Lee", null, null]` (타자 실종, 1루 중복 불가)
    *   **올바른 결과**: `final_bases`: `["Kim", "Lee", null]` (타자->1루, 1루주자->2루)
*   **Case 2 (득점 상황)**
    *   상황: 주자 2루(Park), 3루(Choi), 타자(Han) 2루타
    *   이동: 3루 주자(Choi) -> 홈(득점), 2루 주자(Park) -> 홈(득점), 타자(Han) -> 2루
    *   **올바른 결과**: `final_bases`: `[null, "Han", null]`, `runs_scored`: 2
*   **Case 3 (땅볼 아웃)**
    *   상황: 주자 없음, 내야 땅볼
    *   **올바른 결과**: `final_bases`: `[null, null, null]`

[입력 데이터]
[환경] 날씨: {weather}, 바람: {wind}, 심판 존: {zone}
[상황] 아웃: {outs}, {runners_status}
[수비] {defense_lineup}

[투수 {pitcher_name}] {pitch_type}({pitch_location}) | 구속 {velocity}, 구위 {stuff}, 제구 {control}, 멘탈 {mental}
[타자 {batter_name}] 노림수 {aim_type}, 코스 {aim_location} | 컨택 {contact}, 파워 {power}, 스피드 {speed}

[검증 피드백 (이전 시도 실패 사유)]
{validator_feedback}

위 정보를 종합하여 결과를 JSON으로 출력하세요. `final_bases` 포맷(`[1B, 2B, 3B]`)을 절대 엄수하세요.
"""


VALIDATOR_PROMPT = """
당신은 **야구 규칙 전문가(Baseball Rule Expert)**이자 **데이터 검증관**입니다.
직전의 게임 상황과 시뮬레이션 결과(`SimulationResult`)를 비교하여 **논리적 오류**나 **규칙 위반**이 없는지 검증하세요.

**[필수 검증 항목 (Critical Check)]**
1.  **Hit & Runner Logic**: 결과가 **안타(1B/2B/3B)** 또는 **볼넷(BB)**인데, `final_bases`에 **타자 이름이 없는가?** -> 무조건 **Invalid** (LogicError).
    *   "안타를 쳤는데 주자가 없다"는 명백한 오류입니다. 타자는 루상에 있어야 합니다.
2.  **Runner Continuity**: 주자가 갑자기 사라지거나(Out 없이), 1루에서 3루로 점프(2루타 이상 없이)했는가?
3.  **Base Overlap**: 한 베이스에 이름이 두 개인가? (시스템상 리스트라 불가능하지만 논리적으로 체크)
4.  **Score Mismatch**: `runs_scored` 점수와 실제로 홈에 들어온 주자 수가 일치하는가?

[직전 상황]
- 아웃: {outs}, 주자: {runners_before}

[시뮬레이션 판정 결과]
- 결과: {result_code} ({description})
- 최종 주자 목록(final_bases): {final_bases}
- 득점: {runs_scored}

문제가 있다면 `is_valid: false`와 함께 `correction_suggestion`에 "타자 {batter_name}을 1루에 배치하세요" 처럼 구체적으로 지시하세요.
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
    
        # 재시도인 경우 피드백 가져오기
        val_res = state.get("validator_result")
        feedback = ""
        if val_res and not val_res.is_valid:
            feedback = f"⚠️ [PREVIOUS FAILED]: {val_res.error_type} - {val_res.correction_suggestion}"
        
        runners_status = f"주자: 1루[{runners['runner_1']}], 2루[{runners['runner_2']}], 3루[{runners['runner_3']}]"

        res = chain.invoke({
            "weather": ctx.weather,
            "wind": ctx.wind_direction,
            "zone": ctx.umpire_zone,
            "outs": game.outs,
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
        
        # [Data Integrity] Store the result in GameState for Runner to pick up
        game.last_result = res
        
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

        # [DEBUG] 제거
        
        # 이름으로 매핑 (동명이인 처리 안됨 - 일단 이름 유니크 가정)
        # LLM이 띄어쓰기나 대소문자를 틀릴 수 있으므로 정규화해서 매핑
        def normalize_name(n):
            return n.replace(" ", "").lower() if n else ""
            
        player_map = {normalize_name(p.character.name): p for p in potential_runners}
        
        new_bases_objs = [None, None, None]
        
        for i, r_name in enumerate(res.final_bases):
            if not r_name:
                continue
                
            norm_name = normalize_name(r_name)
            
            if norm_name in player_map:
                new_bases_objs[i] = player_map[norm_name]
            elif norm_name == normalize_name(batter.character.name): # 타자가 나갔을 경우 (위에서 cover되지만 안전장치)
                new_bases_objs[i] = batter
            else:
                # 매핑 실패! (심각한 오류)
                print(f"🚨 [CRITICAL] Runner Name Mismatch: '{r_name}' not found in {[p.character.name for p in potential_runners]}")
                # 일단 이름이 비슷하면 찾아보는 로직 추가 가능하지만, 지금은 로그만 남김
                
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
def run_engine(
    game_state: GameState, 
    db_session: Optional[Any] = None,
    on_step_callback=None
) -> GameState:
    """
    API에서 호출 가능한 시뮬레이션 엔진 진입점.
    initial_game_state: DB에서 로드/변환된 초기 게임 상태
    on_step_callback: 매 스텝(타석)이 끝날 때마다 호출되는 콜백 함수 (DB 저장용) func(game_state: GameState)
    """
    print(f"--- Engine Triggered for Match {game_state.match_id} ---")
    
    # [LOG DEBUG] 명확한 로그 구분을 위해 헤더 추가
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
    for s in app.stream(initial_state, config={"recursion_limit": 1000}):
        # s is a dict of updated state keys
        
        # 'update_state' 노드가 실행된 직후에 DB 저장 등 콜백 호출
        if "update_state" in s:
            updated_game = s["update_state"]["game"]
            if on_step_callback:
                on_step_callback(updated_game)
            step_count += 1
            
    print(f"--- Simulation Finished (Steps: {step_count}) ---")
    print(f"Final Score: {game_state.away_team.name} {game_state.away_score} : {game_state.home_score} {game_state.home_team.name}")
    return game_state

def run_simulation_cli():
    """Local CLI Test Entry"""
    print("--- Multi-Agent Engine Start (CLI) ---")
    # Clear Logs
    with open("simulation_log.txt", "w", encoding="utf-8") as f:
        f.write("=== Simulation Start ===\n")
    with open("broadcast_data.jsonl", "w", encoding="utf-8") as f:
        pass

    game = init_dummy_game()
    # Call run_engine without callback for CLI
    run_engine(game)

if __name__ == "__main__":
    import traceback
    try:
        run_simulation_cli()
    except Exception as e:
        err_msg = traceback.format_exc()
        with open("error_log.txt", "w", encoding="utf-8") as f:
            f.write(err_msg)
        print(f"CRITICAL ERROR in Main Loop: {e}")
