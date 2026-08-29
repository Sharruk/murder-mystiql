export type Screen = "landing" | "workspace" | "leaderboard" | "organizer" | "quiz";

export interface Participant {
  id: string;
  firebase_uid: string;
  email: string;
  display_name: string | null;
  photo_url: string | null;
  is_qualified: boolean;
}

export interface HintItem {
  id: string;
  title: string;
  penalty_minutes: number;
  unlocked: boolean;
  body: string | null;
}

export interface GameState {
  session_id: string;
  event: {
    name: string;
    slug: string;
    tagline: string;
    description: string;
    disclaimer?: string;
    status: string;
  };
  team_name: string;
  participant?: Participant | null;
  quiz_passed?: boolean;
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
  hints?: HintItem[];
  current_level: {
    id: string;
    level_number: number;
    title: string;
    narrative_context: string | null;
    objective: string;
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
  description?: string;
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

export interface QuizOption {
  id: string;
  option_text: string;
}

export interface QuizQuestion {
  id: string;
  prompt: string;
  points: number;
  options: QuizOption[];
}