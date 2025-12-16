# 모노레포 프로젝트 (Monorepo Project)

이 프로젝트는 Next.js 웹 애플리케이션과 FastAPI 백엔드(MariaDB 포함)를 포함하는 모노레포입니다.

## 폴더 구조 (Structure)

```
repo/
  apps/
    api/    # FastAPI 백엔드
    web/    # Next.js 프론트엔드
  infra/    # 인프라 (Docker, Database)
```

## 시작하기 (Getting Started)

이 프로젝트를 로컬 환경에서 설정하고 실행하는 방법입니다.

### 사전 요구사항 (Prerequisites)

- [Docker & Docker Compose](https://www.docker.com/products/docker-desktop/)
- [Node.js](https://nodejs.org/) (v18 이상)

### 환경 설정 (Environment Setup)

이 프로젝트에는 간편한 설정을 위해 환경 변수 기본값이 플레이스홀더로 지정되어 있습니다.

1.  보안이 필요한 경우 `.env.example`을 복사하여 `.env`를 만드세요 (로컬 개발 시 선택 사항).

### Docker로 실행하기 (백엔드 권장)

데이터베이스와 API는 Docker를 사용하여 실행하고, 웹 앱은 로컬에서 실행하면 더 빠른 개발 피드백을 받을 수 있습니다.

1.  **인프라 시작**:

    ```bash
    cd infra
    docker-compose up --build
    ```

    _(만약 `docker-compose` 명령어가 없으면 `docker compose`를 시도해보세요)_

2.  **웹 앱 시작**:
    새 터미널을 열고 다음을 실행하세요:
    ```bash
    cd apps/web
    npm install
    npm run dev
    ```
    [http://localhost:3000](http://localhost:3000)에서 웹 앱에 접속할 수 있습니다.

### 문제 해결 (Troubleshooting)

- **`winner_team_id` 오류**: 스키마 수정으로 해결되었습니다. 만약 DB 오류가 계속되면 `docker-compose down -v`를 실행하여 볼륨을 초기화하세요.
- **`docker-credential-desktop` 오류**: `~/.docker/config.json` 파일을 열고 `credsStore` 항목을 삭제하세요.

## 데이터베이스 스키마 (Database Schema)

```mermaid
erDiagram
    accounts {
        bigint account_id PK
        varchar google_sub UK
        varchar email UK
        varchar display_name
        varchar avatar_url
    }
    worlds {
        bigint world_id PK
        varchar world_name UK
    }
    teams {
        bigint team_id PK
        bigint world_id FK
        varchar team_name
        int min_players
        int max_players
        bigint user_character_id
    }
    characters {
        bigint character_id PK
        bigint world_id FK
        bigint owner_account_id FK
        boolean is_user_created
        varchar nickname
        int contact
        int power
        int speed
    }
    team_players {
        bigint team_player_id PK
        bigint team_id FK
        bigint character_id FK
        enum role
        boolean is_active
    }
    matches {
        bigint match_id PK
        bigint world_id FK
        bigint home_team_id FK
        bigint away_team_id FK
        enum status
        int home_score
        int away_score
        bigint winner_team_id
        bigint loser_team_id
    }
    plate_appearances {
        bigint pa_id PK
        bigint match_id FK
        int inning
        enum half
        int seq
        bigint batter_character_id FK
        enum result_code
    }
    trainings {
        bigint training_id PK
        varchar train_name UK
        int contact_delta
        int power_delta
        int speed_delta
    }
    training_sessions {
        bigint training_session_id PK
        bigint character_id FK
        bigint training_id FK
        datetime performed_at
    }

    accounts ||--o{ characters : "owns"
    worlds ||--o{ teams : "contains"
    worlds ||--o{ characters : "contains"
    worlds ||--o{ matches : "hosts"
    teams ||--o{ team_players : "has roster"
    teams ||--o{ matches : "home team"
    teams ||--o{ matches : "away team"
    characters ||--o{ team_players : "joins"
    characters ||--o{ plate_appearances : "bats"
    characters ||--o{ training_sessions : "trains"
    trainings ||--o{ training_sessions : "defines"
    matches ||--o{ plate_appearances : "logs"
```
