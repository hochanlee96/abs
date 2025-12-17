# 📄 변경사항 명세서 (Phase 2: Realism & Stability Upgrade)

**기간**: GitHub Main 병합 시점 ~ 현재 (검증 에이전트 구현 완료)
**목표**: LLM 시뮬레이션의 현실성(Realism) 강화 및 논리적 데이터 정합성(Stability) 확보

---

## 1. 🏗️ 데이터 모델 (`models.py`)

### 1-1. `SimulationResult` (수정)
LLM이 결과를 생성할 때 '생각(Thinking)'을 먼저 하도록 구조를 변경했습니다.
- **[ADDED]** `reasoning` (str): Chain of Thought(CoT) 추론 과정을 담는 필드.
  - *목적*: "안타"라는 결과를 내기 전, 투수 구위 vs 타자 컨택 등을 분석한 근거를 확보.

### 1-2. `ValidatorResult` (신규)
야구 규칙 검증 에이전트의 출력을 담는 모델을 신규 정의했습니다.
- **[NEW]** `class ValidatorResult`
  - `is_valid` (bool): 규칙 준수 여부.
  - `reasoning` (str): 검증/판단 근거.
  - `error_type` (str): 오류 유형 (LogicError, RuleViolation 등).
  - `correction_suggestion` (str): 수정 제안.

### 1-3. `ManagerDecision` (수정)
감독이 투수 교체를 결정할 수 있도록 필드를 추가했습니다.
- **[ADDED]** `change_pitcher` (bool): 투수 교체 여부 플래그.

---

## 2. ⚙️ 엔진 로직 (`engine.py`)

### 2-1. 프롬프트 엔지니어링 (Prompt Logic Injection)
- **`RESOLVER_PROMPT` 고도화**:
  - **CoT 도입**: `reasoning` 필드 작성을 위한 Step-by-Step 지침 추가.
  - **Defensive Context**: 수비수 능력치(범위, 어깨)를 프롬프트에 동적으로 주입.
  - **Scenario Guidelines**: 내야 땅볼, 외야 뜬공 등 상황별 주자 이동 가이드라인 추가.
- **`VALIDATOR_PROMPT` 신규 작성**:
  - 이전 상황(아웃, 주자)과 현재 결과(Result)를 비교하여 논리적 모순(예: 주자 증발, 3아웃 후 진행)을 탐지하도록 지시.

### 2-2. 노드(Node) 및 그래프(Graph) 구조 변경
- **[NEW] `validator_node`**:
  - `resolver_node` 다음 단계에 배치.
  - LLM을 통해 결과의 정합성을 판별하고, 실패 시 Warning 로그를 남김.
- **[MODIFIED] `update_state_node`**:
  - 투수 체력(Stamina) 감소 로직 적용 (투구 수 비례 감소).
  - 감독의 `change_pitcher` 결정 시 실제 투수 객체를 교체하는 로직 추가.

### 2-3. 자가 수정(Self-Correction) 메커니즘
- **[NEW] `route_validator` & Conditional Edge**:
  - 검증 실패(`is_valid=False`) 시 다음 단계로 가지 않고 `resolver_node`로 회귀(Backtracking).
  - **Retry Count**: `SimState`에 `retry_count`를 추가하여 최대 3회까지 재시도 허용 (무한 루프 방지).

### 2-4. 상태 관리 (`SimState`)
- **[ADDED]** `validator_result`: 검증 결과 저장.
- **[ADDED]** `retry_count`: 재시도 횟수 트래킹.

---

## 3. 🛡️ 로깅 및 디버깅 시스템

- **`simulation_log.txt`**: 단순 에러 로그를 넘어, 경기 중계 및 검증 경고(`[Validation Warning]`)를 실시간 기록.
- **`error_log.txt`**: 노드별 `try-except` 블록을 통해 치명적 오류 발생 시 Traceback을 별도 파일로 격리 저장.
- **검증 스크립트**:
  - `verify_cot.py`: CoT 필드 출력 여부 확인.
  - `inspect_json.py`: JSONL 데이터 구조 검사.

---

## 4. 📊 요약

| 구분 | 주요 변경 사항 | 비고 |
| :--- | :--- | :--- |
| **Logic** | CoT 적용, Validator 등판, Retry Loop 구현 | "생각하는 엔진" 및 "스스로 고치는 엔진" 구현 |
| **Data** | Player Stats 확장, SimulationResult 확장 | 투수 체력/구종, 수비 스탯 반영 |
| **System** | Error Handling 강화, Logging 세분화 | 멈추지 않는 시뮬레이션을 위한 안정장치 |

현재 시스템은 **"1회초/말 전체 진행"** 및 **"오류 발생 시 재시도"**가 가능한 상태입니다.
다음 단계는 이 데이터를 영구 보존하기 위한 **DB 스키마 설계 및 연동**입니다.
