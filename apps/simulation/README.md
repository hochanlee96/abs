# 매치 시뮬레이션 엔진 (Match Simulation Engine)

이 디렉토리는 야구 경기의 타석별 결과를 **LangGraph**와 **LLM**을 이용해 시뮬레이션하는 엔진입니다.
프론트엔드/백엔드와의 연동 없이 독립적으로 동작하며, 결과 데이터를 JSON 형태로 생성합니다.

## 1. 환경 설정 (Setup)

### 필수 요구사항
- Python 3.9+
- OpenAI API Key

### 설치 및 실행
```bash
# 1. 가상환경 생성 (선택)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 환경 변수 설정 (.env 파일 생성)
# apps/simulation/.env 파일을 생성하고 아래 내용을 추가하세요.
OPENAI_API_KEY=sk-proj-...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=...
```

## 2. 데이터 연동 명세 (Integration Spec)

시뮬레이션 엔진은 매 타석 결과와 **다음 타자 정보**를 포함한 `BroadcastData` 구조를 따릅니다.
프론트엔드는 이 데이터를 받아 실시간 중계 화면을 구성할 수 있습니다.

### JSON 데이터 예시 (Output Format)

```json
{
  "match_id": "game-uuid-1234",
  "inning": 1,
  "half": "TOP", 
  "outs": 0,
  "home_score": 0,
  "away_score": 1,
  "result": {
    "result_code": "HIT_DOUBLE",
    "description": "우중간을 완전히 가르는 2루타! 주자들 모두 홈으로 쇄도합니다.",
    "runs_scored": 1,
    "runners_advanced": true
  },
  "current_batter": {
    "name": "홍길동",
    "role": "BATTER",
    "stats": { "contact": 85, "power": 70, "speed": 60 }
  },
  "current_pitcher": {
    "name": "김철수",
    "role": "PITCHER",
    "stats": { "control": 80, "stuff": 75, "velocity": 150 }
  },
  "next_batter": {
    "name": "이영희",
    "role": "BATTER",
    "stats": { "contact": 90, "power": 60, "speed": 80 }
  }
}
```

### 주요 필드 설명
- **`result`**: 해당 타석의 최종 결과와 중계 멘트(`description`).
- **`next_batter`**: **[프론트 요청]** 다음 타석에 들어설 타자의 정보 (미리 보여주기 위함).
- **`stats`**: 시뮬레이션에 사용된 능력치 (투수: 구위/구속/제구, 타자: 컨택/파워/스피드).

## 3. 개발 가이드 (Development Guide)

### 파일 구조
- `engine.py`: **LangGraph** 로직의 핵심입니다. `at_bat_node` -> `update_state_node` -> `check_inning_node` 순서로 순환합니다.
- `models.py`: Pydantic 데이터 모델 정의. DB 스키마와 최대한 호환되도록 설계되었습니다.
- `dummy_generator.py`: 테스트를 위한 가상 팀/선수 데이터 생성기.

### 시뮬레이션 로직 (Multi-Agent System)
규칙 기반 확률 계산을 배제하고, 다음 5개 에이전트의 연쇄 작용(Chain of Thought)으로 결과를 도출합니다.

1.  **Director (총괄)**: 날씨(비, 바람), 심판 판정 성향(Zone) 등 환경 변수 설정.
2.  **Manager (감독)**: 점수차와 상황에 따른 작전 지시 (번트, 전진수비, 장타 노림 등).
3.  **Pitcher (투수)**: 구종(직구/변화구), 코스, 완급 조절 선택 (제구력에 따른 실투 가능성).
4.  **Batter (타자)**: 노림수(구종/코스 예측), 타격 스타일(적극/신중) 결정.
5.  **Resolver (판정)**: 위 모든 의도와 변수를 종합하여 LLM이 최종 결과를 물리적으로 추론.

> **Note**: 재귀 제한(recursion_limit)을 1000으로 설정하여 연장전 등 긴 경기 흐름을 지원합니다.
