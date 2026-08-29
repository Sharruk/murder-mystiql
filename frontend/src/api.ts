import type { GameState, InvestigationTable, LeaderboardEntry, QueryResult } from "./types";

interface ApiErrorShape {
  detail?: { message?: string } | string;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options?.headers ?? {}) },
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
  start: (teamName: string) =>
    request<{ session: GameState }>("/api/game/start", {
      method: "POST",
      body: JSON.stringify({ team_name: teamName }),
    }),
  state: (sessionId: string) => request<{ session: GameState }>(`/api/game/state?session_id=${encodeURIComponent(sessionId)}`),
  tables: (sessionId: string) =>
    request<{ available_tables: InvestigationTable[]; locked_table_count: number }>(
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
  finish: (sessionId: string) =>
    request<{ session: GameState }>("/api/game/finish", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId }),
    }),
  leaderboard: () => request<{ entries: LeaderboardEntry[] }>("/api/leaderboard"),
};