import type {
  GameState,
  InvestigationTable,
  LeaderboardEntry,
  Participant,
  QueryResult,
  QuizQuestion,
} from "./types";

const TOKEN_KEY = "murder_mystiql_jwt_token";

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

interface ApiErrorShape {
  detail?: { message?: string; code?: string } | string;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getStoredToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options?.headers as Record<string, string> ?? {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(path, {
    ...options,
    headers,
  });

  const body = (await response.json().catch(() => ({}))) as T & ApiErrorShape;
  if (!response.ok) {
    const detail = body.detail;
    const message = typeof detail === "string" ? detail : detail?.message;
    throw new Error(message || "Something went wrong. Please try again.");
  }
  return body;
}

export const api = {
  // Authentication
  verifyAuth: (idToken: string) =>
    request<{ token: string; participant: Participant; session: GameState }>("/api/auth/verify", {
      method: "POST",
      body: JSON.stringify({ id_token: idToken }),
    }),

  getMe: () =>
    request<{ participant: Participant; session: GameState | null }>("/api/auth/me"),

  logout: () =>
    request<{ status: string }>("/api/auth/logout", {
      method: "POST",
    }),

  // Game & Investigation
  start: (teamName?: string) =>
    request<{ session: GameState }>("/api/game/start", {
      method: "POST",
      body: JSON.stringify({ team_name: teamName || "" }),
    }),

  state: (sessionId: string) =>
    request<{ session: GameState }>(`/api/game/state?session_id=${encodeURIComponent(sessionId)}`),

  tables: (sessionId: string) =>
    request<{ available_tables: InvestigationTable[]; locked_table_count: number; total_tables: number }>(
      `/api/schema/tables?session_id=${encodeURIComponent(sessionId)}`,
    ),

  query: (sessionId: string, query: string) =>
    request<QueryResult>("/api/query/execute", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, query }),
    }),

  answer: (sessionId: string, answer: string) =>
    request<{ correct: boolean; penalty_seconds: number; lock_seconds: number; state: GameState }>("/api/answer/submit", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, answer }),
    }),

  useHint: (sessionId: string, hintId: string) =>
    request<{ hint_id: string; title: string; body: string; penalty_seconds: number; state: GameState }>("/api/hint/use", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, hint_id: hintId }),
    }),

  finish: (sessionId: string) =>
    request<{ session: GameState }>("/api/game/finish", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId }),
    }),

  leaderboard: () =>
    request<{ event: { name: string; slug: string; disclaimer?: string }; entries: LeaderboardEntry[] }>("/api/leaderboard"),

  quizQuestions: () =>
    request<{ questions: QuizQuestion[] }>("/api/quiz/questions"),

  quizSubmit: (sessionId: string, answers: Record<string, string>) =>
    request<{ score: number; total_questions: number; qualify_score: number; qualified: boolean; state: GameState }>(
      "/api/quiz/submit",
      {
        method: "POST",
        body: JSON.stringify({ session_id: sessionId, answers }),
      },
    ),

  organizerStats: () =>
    request<{
      event_name: string;
      total_sessions: number;
      active_sessions: number;
      completed_sessions: number;
      total_levels: number;
      total_tables: number;
      wrong_penalty_minutes: number;
      hint_penalty_minutes: number;
      leaderboard: LeaderboardEntry[];
    }>("/api/organizer/stats"),
};