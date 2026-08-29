export type Screen = "landing" | "workspace" | "leaderboard" | "organizer";

export interface GameState {
  session_id: string;
  event: {
    name: string;
    slug: string;
    tagline: string;
    description: string;
    status: string;
  };
  team_name: string;
  status: "IN_PROGRESS" | "COMPLETED" | "FINISHED";
  started_at: string;
  finish_at: string | null;
  current_level_number: number;
  total_levels: number;
  completed_levels: number;
  actual_duration_seconds: number;
  wrong_submission_count: number;
  wrong_penalty_seconds: number;
  hint_penalty_seconds: number;
  effective_time_seconds: number;
  submission_lock_remaining_seconds: number;
  has_configured_case: boolean;
  current_level: {
    id: string;
    level_number: number;
    title: string;
    description: string | null;
    clue: string | null;
    answer_type: string;
  } | null;
}

export interface TableColumn {
  name: string;
  data_type: string;
  nullable: boolean;
  is_primary_key: boolean;
}

export interface InvestigationTable {
  name: string;
  label: string;
  unlock_level: number;
  columns: TableColumn[];
}

export interface QueryResult {
  columns: string[];
  rows: unknown[][];
  row_count: number;
  duration_ms: number;
  max_rows: number;
}

export interface LeaderboardEntry {
  rank: number;
  team_name: string;
  current_level: number;
  total_levels: number;
  progress_percent: number;
  effective_time_seconds: number;
  status: string;
}