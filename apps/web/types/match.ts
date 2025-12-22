export type MatchEventType = 'CONNECTED' | 'START' | 'PA' | 'FINAL' | 'ERROR' | 'ROSTERS';

export interface PlayerInfo {
    name: string;
    role: string;
    stats: Record<string, number>;
}

export interface RunnerInfo {
    name: string;
}

export interface SimulationResult {
    result_code: string;
    description: string;
    runners_advanced?: boolean;
    final_bases?: (string | null)[];
    runs_scored: number;
    pitch_desc?: string;
    hit_desc?: string;
}

export interface BroadcastData {
    match_id: string;
    inning: number;
    half: 'TOP' | 'BOTTOM';
    outs: number;
    home_score: number;
    away_score: number;
    current_batter: PlayerInfo;
    current_pitcher: PlayerInfo;
    runners: (RunnerInfo | null)[];
    result: SimulationResult;
    next_batter: PlayerInfo;
}

export interface MatchEventMessage {
    type: MatchEventType;
    data?: BroadcastData;
    scores?: { home: number; away: number };
    message?: string;
    home?: PlayerInfo[];
    away?: PlayerInfo[];
}

export interface Character {
    character_id: number;
    nickname: string;
    position_main: string;
    total_hits: number;
    total_ab: number;
    total_earned_runs: number;
    total_outs_pitched: number;
    // Add other fields if needed for display
}

export interface TeamPlayer {
    character: Character;
    role: string;
    is_active: boolean;
}

export interface Team {
    team_name: string;
    team_players: TeamPlayer[];
}

export interface MatchDetail {
    match_id: number;
    home_team: Team;
    away_team: Team;
    game_state: {
        logs: BroadcastData[];
    };
    status: string;
    home_score: number;
    away_score: number;
}
