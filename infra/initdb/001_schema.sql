-- =========================================================
-- 001_schema.sql (MariaDB 10.11+)
-- =========================================================

SET NAMES utf8mb4;
SET time_zone = '+00:00';

-- =========================
-- 1) Accounts (Google SSO)
-- =========================
CREATE TABLE accounts (
  account_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  google_sub VARCHAR(64) NOT NULL,           -- Google "sub" unique id
  email VARCHAR(255) NULL,
  display_name VARCHAR(100) NULL,
  avatar_url VARCHAR(500) NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (account_id),
  UNIQUE KEY uk_accounts_google_sub (google_sub),
  UNIQUE KEY uk_accounts_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================
-- 2) Worlds
-- =========================
CREATE TABLE worlds (
  world_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  world_name VARCHAR(100) NOT NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (world_id),
  UNIQUE KEY uk_worlds_name (world_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================
-- 3) Teams
-- =========================
CREATE TABLE teams (
  team_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  world_id BIGINT UNSIGNED NOT NULL,
  team_name VARCHAR(80) NOT NULL,

  min_players INT NOT NULL DEFAULT 9,
  max_players INT NOT NULL DEFAULT 25,

  -- MVP: 팀당 유저 1명 UX를 쉽게 만들기 위한 "포인터" 컬럼
  -- (FK는 team_players로 보장하고, 여기서는 참조용으로만 씀)
  user_character_id BIGINT UNSIGNED NULL,

  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),

  PRIMARY KEY (team_id),
  UNIQUE KEY uk_teams_world_name (world_id, team_name),
  KEY idx_teams_world (world_id),

  CONSTRAINT fk_teams_world
    FOREIGN KEY (world_id) REFERENCES worlds(world_id)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================
-- 4) Characters
-- =========================
CREATE TABLE characters (
  character_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  world_id BIGINT UNSIGNED NOT NULL,

  -- 유저 소유면 owner_account_id 채움 / AI 캐릭터면 NULL
  owner_account_id BIGINT UNSIGNED NULL,

  -- "유저가 생성한 캐릭터"인지 (AI 생성과 구분)
  is_user_created BOOLEAN NOT NULL DEFAULT 0,

  nickname VARCHAR(60) NOT NULL,
  age INT NULL,

  contact INT NOT NULL DEFAULT 0,
  power INT NOT NULL DEFAULT 0,
  speed INT NOT NULL DEFAULT 0,

  -- [Phase 2] Extended Stats for Simulation
  -- Common
  mental INT NOT NULL DEFAULT 50,
  recovery INT NOT NULL DEFAULT 50,
  
  -- Pitcher Specific
  stamina INT NOT NULL DEFAULT 100,
  velocity_max INT NOT NULL DEFAULT 140,
  pitch_fastball INT NOT NULL DEFAULT 0,
  pitch_slider INT NOT NULL DEFAULT 0,
  pitch_curve INT NOT NULL DEFAULT 0,
  pitch_changeup INT NOT NULL DEFAULT 0,
  pitch_splitter INT NOT NULL DEFAULT 0,

  -- Batter Specific
  eye INT NOT NULL DEFAULT 50,
  clutch INT NOT NULL DEFAULT 50,
  contact_left INT NOT NULL DEFAULT 0,
  contact_right INT NOT NULL DEFAULT 0,
  power_left INT NOT NULL DEFAULT 0,
  power_right INT NOT NULL DEFAULT 0,

  -- Fielder Specific
  defense_range INT NOT NULL DEFAULT 50,
  defense_error INT NOT NULL DEFAULT 50,
  defense_arm INT NOT NULL DEFAULT 50,
  position_main VARCHAR(20) NOT NULL DEFAULT 'DH',
  position_sub VARCHAR(20) NULL,
  
  -- [Phase 3] Season Stats (Accumulated)
  games_played INT NOT NULL DEFAULT 0,
  at_bats INT NOT NULL DEFAULT 0,
  hits INT NOT NULL DEFAULT 0,
  homeruns INT NOT NULL DEFAULT 0,
  rbis INT NOT NULL DEFAULT 0,
  runs INT NOT NULL DEFAULT 0,
  walks INT NOT NULL DEFAULT 0,
  strikeouts INT NOT NULL DEFAULT 0,

  contact_exp INT NOT NULL DEFAULT 0,
  power_exp INT NOT NULL DEFAULT 0,
  speed_exp INT NOT NULL DEFAULT 0,

  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),

  PRIMARY KEY (character_id),
  UNIQUE KEY uk_characters_world_nickname (world_id, nickname),
  KEY idx_characters_owner (owner_account_id),
  KEY idx_characters_world (world_id),

  CONSTRAINT fk_characters_world
    FOREIGN KEY (world_id) REFERENCES worlds(world_id)
    ON DELETE RESTRICT ON UPDATE CASCADE,

  CONSTRAINT fk_characters_owner
    FOREIGN KEY (owner_account_id) REFERENCES accounts(account_id)
    ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================
-- 5) TeamPlayers (Roster)
-- =========================
CREATE TABLE team_players (
  team_player_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  team_id BIGINT UNSIGNED NOT NULL,
  character_id BIGINT UNSIGNED NOT NULL,

  -- MVP: USER는 팀에 1명만 (DB로 강제 어려워 앱 로직에서 강제)
  role ENUM('USER','AI') NOT NULL DEFAULT 'AI',

  joined_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  left_at DATETIME(3) NULL,
  is_active BOOLEAN NOT NULL DEFAULT 1,

  PRIMARY KEY (team_player_id),

  -- 같은 캐릭터가 같은 팀에 "활성"으로 중복 등록되는 걸 방지
  UNIQUE KEY uk_team_players_active (team_id, character_id, is_active),
  KEY idx_team_players_team_active (team_id, is_active),
  KEY idx_team_players_character_active (character_id, is_active),

  CONSTRAINT fk_team_players_team
    FOREIGN KEY (team_id) REFERENCES teams(team_id)
    ON DELETE CASCADE ON UPDATE CASCADE,

  CONSTRAINT fk_team_players_character
    FOREIGN KEY (character_id) REFERENCES characters(character_id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================
-- 6) Matches
-- =========================
CREATE TABLE matches (
  match_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,

  -- 사람이 보는 코드 (원하면 fixture#Home#Away 같은 룰로 채우기)
  match_code VARCHAR(128) NULL,

  world_id BIGINT UNSIGNED NOT NULL,
  home_team_id BIGINT UNSIGNED NOT NULL,
  away_team_id BIGINT UNSIGNED NOT NULL,

  status ENUM('SCHEDULED','IN_PROGRESS','FINISHED','CANCELED') NOT NULL DEFAULT 'SCHEDULED',

  scheduled_at DATETIME(3) NULL,
  started_at DATETIME(3) NULL,
  finished_at DATETIME(3) NULL,

  home_score INT NOT NULL DEFAULT 0,
  away_score INT NOT NULL DEFAULT 0,
  
  -- Current state for simulation (transient)
  game_state JSON NULL,

  -- 무승부 없음: 점수로 winner/loser 파생 (앱 레벨에서 update)
  winner_team_id BIGINT UNSIGNED NULL,
  loser_team_id BIGINT UNSIGNED NULL,

  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

  PRIMARY KEY (match_id),
  UNIQUE KEY uk_matches_match_code (match_code),
  KEY idx_matches_world_status_time (world_id, status, scheduled_at),
  KEY idx_matches_home (home_team_id),
  KEY idx_matches_away (away_team_id),
  KEY idx_matches_winner (winner_team_id),



  CONSTRAINT fk_matches_world
    FOREIGN KEY (world_id) REFERENCES worlds(world_id)
    ON DELETE RESTRICT ON UPDATE CASCADE,

  CONSTRAINT fk_matches_home_team
    FOREIGN KEY (home_team_id) REFERENCES teams(team_id)
    ON DELETE RESTRICT ON UPDATE CASCADE,

  CONSTRAINT fk_matches_away_team
    FOREIGN KEY (away_team_id) REFERENCES teams(team_id)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================
-- 7) Plate Appearances (At-bat log)
-- =========================
CREATE TABLE plate_appearances (
  pa_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  match_id BIGINT UNSIGNED NOT NULL,

  inning INT NOT NULL,
  half ENUM('TOP','BOTTOM') NOT NULL,
  seq INT NOT NULL,

  batter_character_id BIGINT UNSIGNED NOT NULL,

  result_code ENUM(
    'SO','BB','HBP','FO','GO','1B','2B','3B','HOMERUN'
  ) NOT NULL,

  runs_scored INT DEFAULT 0,
  rbi INT DEFAULT 0,
  outs_added INT DEFAULT 0,

  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

  PRIMARY KEY (pa_id),
  UNIQUE KEY uk_pa_match_inning_half_seq (match_id, inning, half, seq),
  KEY idx_pa_match (match_id),
  KEY idx_pa_batter (batter_character_id),

  CONSTRAINT fk_pa_match
    FOREIGN KEY (match_id) REFERENCES matches(match_id)
    ON DELETE CASCADE ON UPDATE CASCADE,

  CONSTRAINT fk_pa_batter
    FOREIGN KEY (batter_character_id) REFERENCES characters(character_id)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================
-- 8) Trainings (definitions)
-- =========================
CREATE TABLE trainings (
  training_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  train_name VARCHAR(60) NOT NULL,
  contact_delta INT NOT NULL DEFAULT 0,
  power_delta INT NOT NULL DEFAULT 0,
  speed_delta INT NOT NULL DEFAULT 0,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (training_id),
  UNIQUE KEY uk_trainings_name (train_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================
-- 9) Training sessions (execution log)
-- =========================
CREATE TABLE training_sessions (
  training_session_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  character_id BIGINT UNSIGNED NOT NULL,
  training_id BIGINT UNSIGNED NOT NULL,

  performed_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

  applied_contact_delta INT NOT NULL DEFAULT 0,
  applied_power_delta INT NOT NULL DEFAULT 0,
  applied_speed_delta INT NOT NULL DEFAULT 0,

  exp_gained_contact INT NOT NULL DEFAULT 0,
  exp_gained_power INT NOT NULL DEFAULT 0,
  exp_gained_speed INT NOT NULL DEFAULT 0,

  PRIMARY KEY (training_session_id),
  KEY idx_training_sessions_character (character_id, performed_at),

  CONSTRAINT fk_training_sessions_character
    FOREIGN KEY (character_id) REFERENCES characters(character_id)
    ON DELETE CASCADE ON UPDATE CASCADE,

  CONSTRAINT fk_training_sessions_training
    FOREIGN KEY (training_id) REFERENCES trainings(training_id)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================
-- (옵션) 샘플 world 하나 넣고 싶으면:
-- INSERT INTO worlds(world_name) VALUES ('default');
-- =========================