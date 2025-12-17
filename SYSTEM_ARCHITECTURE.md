# System Architecture & Diagrams

Here are the UML diagrams representing the key features of the Agentic Baseball Simulator.

## 1. User Onboarding & League Initialization Flow

This sequence diagram illustrates the flow from User Login to the automatic generation of the Baseball League (World, Teams, Matches).

```mermaid
sequenceDiagram
    actor User
    participant Web as Frontend (Next.js)
    participant API as Backend API (FastAPI)
    participant Auth as Auth Module
    participant Service as League Service
    participant DB as MariaDB

    %% Authentication
    User->>Web: Login with Google
    Web->>API: GET /me (id_token)
    API->>Auth: Verify Token
    Auth-->>API: Valid Payload
    API->>DB: Upsert Account
    DB-->>API: Account ID
    API-->>Web: User Profile

    %% Character Creation
    User->>Web: Fill Character Form & Submit
    Web->>API: POST /characters
    API->>DB: Create Character
    DB-->>API: Character Created
    API-->>Web: Character Object

    %% Auto-Initialization
    Note over Web, Service: Triggered automatically after creation
    Web->>API: POST /league/init
    API->>Service: generate_league(user_char_id)

    rect rgb(30, 30, 40)
        note right of Service: World Generation Logic
        Service->>DB: Create unique "World"
        Service->>DB: Generate 4 Teams (Seoul, Busan, etc.)
        Service->>DB: Generate 35+ NPC Characters
        Service->>DB: Assign User to Team 1
        Service->>DB: Generate Round-Robin Schedule (Matches)
    end

    Service-->>API: Success Stats (Teams, Matches count)
    API-->>Web: 200 OK
    Web->>User: Redirect to Dashboard
```

## 2. Database Schema (Entity Relationship)

This ER diagram shows the relationships between the core entities.

```mermaid
erDiagram
    ACCOUNT ||--o{ CHARACTER : owns
    WORLD ||--|{ TEAM : contains
    WORLD ||--|{ CHARACTER : houses
    WORLD ||--|{ MATCH : organizes

    TEAM ||--o{ TEAM_PLAYER : roster
    CHARACTER ||--o{ TEAM_PLAYER : assigned_to

    MATCH }|--|| TEAM : home_team
    MATCH }|--|| TEAM : away_team

    ACCOUNT {
        bigint account_id PK
        string google_sub
        string email
    }

    CHARACTER {
        bigint character_id PK
        string nickname
        int contact
        int power
        int speed
        enum role "PITCHER|BATTER"
    }

    WORLD {
        bigint world_id PK
        string world_name
    }

    TEAM {
        bigint team_id PK
        string team_name
    }

    MATCH {
        bigint match_id PK
        enum status "SCHEDULED|IN_PROGRESS|FINISHED"
        json game_state
        int home_score
        int away_score
    }
```

## 3. Simulation & Gameplay Architecture

This flowchart demonstrates how the "Play Game" feature works, connecting the Frontend, Backend, and the AI Simulation Engine.

```mermaid
flowchart TD
    subgraph Frontend ["Frontend (Dashboard)"]
        PlayBtn["User Clicks 'Play Game'"]
        Poll["Polling Loop (Every 1s)"]
        LogView["Console Log View"]
    end

    subgraph Backend ["Backend API"]
        PostPlay["POST /play"]
        GetMatch["GET /matches/{id}"]
        BgTask["Background Task Runner"]
    end

    subgraph Database ["MariaDB"]
        MatchDB[("Match Table")]
        CharDB[("Character Table")]
    end

    subgraph SimEngine ["Simulation Engine (LangGraph)"]
        Director["Director Agent<br/>(Set Weather/Zone)"]
        Manager["Manager Agents<br/>(Decide Strategy)"]
        Player["Player Agents<br/>(Pitcher/Batter Action)"]
        Resolver["Resolver Engine<br/>(Physics/Rules + LLM)"]
        StateUpdate["State Updater"]
    end

    %% Flow
    PlayBtn -->|id_token + world_id| PostPlay
    PostPlay -->|Get Next Scheduled Match| MatchDB
    PostPlay -->|Trigger Async| BgTask
    BgTask -->|Run Match| Director

    %% Simulation Loop
    Director -->|Load Rosters| CharDB
    Director --> Manager --> Player --> Resolver

    Resolver -->|Reasoning & Result| StateUpdate
    StateUpdate -->|Save Logs & Score| MatchDB

    %% Feedback Loop
    StateUpdate -.->|Next Step| Director

    %% Frontend Polling
    Poll -->|Request Update| GetMatch
    GetMatch -->|Read State| MatchDB
    MatchDB --"Return JSON (Logs)"--> LogView
```
