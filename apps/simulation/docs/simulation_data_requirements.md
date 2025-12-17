# 📄 시뮬레이션 고도화를 위한 데이터 스키마 수정 요청서

**작성일**: 2025-12-17
**요청자**: 매치 엔진 개발팀 (Simulation Engine)
**수신**: 백엔드 & DB 담당자

---

## 1. 개요 (Overview)
현재 시뮬레이션 엔진을 **실제 서비스 가능한 수준의 리얼리티(Realism)**로 고도화하기 위해, DB 스키마의 대대적인 확장이 필요합니다.
기존의 단순 능력치(Power/Contact/Speed)로는 수비, 투수 운용, 구종 싸움 등 야구의 핵심 재미를 구현할 수 없습니다.

아래 명세를 반영하여 **DB 스키마(Prisma) 업데이트** 및 **데이터 주입(Seeding)**을 요청드립니다.

---

## 2. 선수 능력치 확장 (Player Stats Expansion)

모든 능력치는 **0 ~ 100** 사이의 정수값(Int)으로 저장해 주세요.

### 2.1 투수 (Pitcher)
단순 '구위/제구'를 넘어 체력 관리와 구종별 숙련도가 필요합니다.

| 필드명 (Column) | 설명 (Description) | 용도 (Usage) |
| :--- | :--- | :--- |
| `stamina` | **체력** | 투구수 증가에 따른 구위 하락폭 결정 (선발/불펜 운용 핵심) |
| `mental` | **멘탈/위기관리** | 주자가 있을 때 능력치 하락 방어 (클러치 상황) |
| `recovery` | **회복력** | 연투 가능 여부 판단 (불펜 투수) |
| `velocity_max` | **최고 구속** | 실제 구속(km/h) 시뮬레이션용 (예: 155) |
| `pitch_fastball` | 직구 숙련도 | 높을수록 안타 확률 감소 및 제구 향상 (S급=90+) |
| `pitch_slider` | 슬라이더 숙련도 | 변화구 무브먼트 및 헛스윙 유도 확률 |
| `pitch_curve` | 커브 숙련도 | " |
| `pitch_changeup` | 체인지업 숙련도 | " |
| `pitch_splitter` | 스플리터 숙련도 | " |

### 2.2 타자 (Batter)
타격의 정교함과 상황 대처 능력을 추가합니다.

| 필드명 (Column) | 설명 (Description) | 용도 (Usage) |
| :--- | :--- | :--- |
| `eye` | **선구안** | 볼넷 골라내기 및 나쁜 공 컨택 능력 |
| `clutch` | **클러치/득점권** | 득점권 상황(RISP)에서의 타격 보정치 |
| `contact_left` | **좌투수 컨택** | 좌완 투수 상대 시 보정 |
| `contact_right` | **우투수 컨택** | 우완 투수 상대 시 보정 |
| `power_left` | **좌투수 파워** | " |
| `power_right` | **우투수 파워** | " |

### 2.3 수비수 (Fielder) - **[신규 필수]**
**현재 수비 관련 스탯이 전무하여, 타구가 발생해도 수비 시뮬레이션을 할 수 없습니다.**

| 필드명 (Column) | 설명 (Description) | 용도 (Usage) |
| :--- | :--- | :--- |
| `defense_range` | **수비 범위** | 안타성 타구를 따라가서 잡을 확률 (가장 중요) |
| `defense_error` | **포구 실책** | 잡은 공을 놓칠 확률 (에러 발생) |
| `defense_arm` | **송구력 (어깨)** | 깊은 타구 처리 시 아웃/세이프 결정, 외야수의 홈 보살 |
| `position_main` | **주 포지션** | 해당 포지션 수비 시 페널티 없음 (예: 'SS') |
| `position_sub` | **부 포지션** | 약간의 페널티 적용 (예: '2B') |

---

## 3. 경기 결과 데이터 (Match Log Schema)

시뮬레이션 엔진이 생성한 결과 데이터를 저장할 테이블 구조입니다. 프론트엔드 중계와 직결됩니다.

### 3.1 Play-by-Play Log (매 타석 로그)
`MatchLog` 또는 `PlayRecord` 테이블 신설 요청

```json
{
  "match_id": "UUID",
  "inning": 1,
  "half": "TOP", // 초/말
  "pitcher_id": "UUID",
  "batter_id": "UUID",
  "result_code": "HIT_DOUBLE", // 안타, 아웃 등 코드
  "description": "우중간을 가르는 2루타! 주자 일소!", // LLM이 생성한 텍스트
  "runners_state": "[null, 'player_id_1', 'player_id_2']", // 당시 주자 상황
  "score_change": 1, // 해당 플레이로 난 점수
  "created_at": "Timestamp"
}
```

---

## 4. 시스템 연동 요구사항 (System Requirements)

1.  **초기 데이터 주입 (Seeding)**
    - 위 확장된 필드들에 대해 랜덤 또는 더미 값(40~90 사이)을 채워주세요. (NULL 값 금지)
2.  **API 엔드포인트**
    - `GET /api/simulation/roster/{team_id}`: 위에 요청한 **모든 확장 능력치를 포함**한 선수단 정보 반환.
3.  **저장 로직**
    - 시뮬레이션 엔진이 경기 종료 후(또는 이닝 종료 후) 한 번에 로그를 보낼 수 있는 `POST /api/simulation/match-result` 필요.

감사합니다.
