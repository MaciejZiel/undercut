import type { components } from "@/lib/api/client";
import { apiJson, apiRequest } from "@/lib/auth/http";

type S = components["schemas"];
export type RoundState = S["RoundState"];
export type PickInput = S["PickInput"];
export type PickDriver = S["PickDriver"];
export type HistoryRow = S["HistoryRow"];
export type Leaderboard = S["Leaderboard"];
export type LeaderboardRow = S["LeaderboardRow"];
export type LeagueDetail = S["LeagueDetail"];
export type LeagueSummary = S["LeagueSummary"];
export type MemberPick = S["MemberPick"];
export type Pick = S["Pick"];
export type SlotKey = "p1" | "p2" | "p3" | "pole" | "fastest_lap";

export const SLOTS: { key: SlotKey; label: string; podium: boolean }[] = [
  { key: "p1", label: "Winner (P1)", podium: true },
  { key: "p2", label: "Second place (P2)", podium: true },
  { key: "p3", label: "Third place (P3)", podium: true },
  { key: "pole", label: "Pole position", podium: false },
  { key: "fastest_lap", label: "Fastest lap", podium: false },
];

/** Keys of per-user prediction data in the query cache (all start with "predict" / "leagues"). */
export const predictKeys = {
  round: (year: number, round: number) => ["predict", "round", year, round] as const,
  next: ["predict", "next"] as const,
  drivers: (year: number) => ["predict", "drivers", year] as const,
  history: ["predict", "history"] as const,
  leaderboard: (p: LeaderboardParams) => ["predict", "leaderboard", p] as const,
  leagues: ["leagues"] as const,
  league: (code: string) => ["leagues", code] as const,
  leaguePicks: (code: string, year: number, round: number) => ["leagues", code, "picks", year, round] as const,
  seasons: ["predict", "seasons"] as const,
  season: (year: number) => ["predict", "season", year] as const,
};

export type RoundStateResult = {
  state: RoundState;
  /** Server time minus browser time in ms, from the response's Date header. Only used to display the countdown. */
  skewMs: number;
};

export function serverSkew(response: Response): number {
  const header = response.headers.get("Date");
  const server = header ? Date.parse(header) : NaN;
  return Number.isFinite(server) ? server - Date.now() : 0;
}

export async function fetchRoundState(year: number, round: number): Promise<RoundStateResult> {
  const { data, response } = await apiRequest<RoundState>(`/api/v1/predictions/rounds/${year}/${round}/`);
  return { state: data, skewMs: serverSkew(response) };
}

export async function submitPick(year: number, round: number, pick: PickInput): Promise<{ state: RoundState; created: boolean }> {
  const { data, status } = await apiRequest<RoundState>(`/api/v1/predictions/rounds/${year}/${round}/`, { method: "PUT", body: pick });
  return { state: data, created: status === 201 };
}

/** Milliseconds until the lock, by the server's clock (as far as the response said). Never negative. */
export function remainingMs(closesAt: string | null, skewMs: number, nowMs: number = Date.now()): number | null {
  if (!closesAt) return null;
  const t = Date.parse(closesAt);
  if (!Number.isFinite(t)) return null;
  return Math.max(0, t - (nowMs + skewMs));
}

export function formatCountdown(ms: number): string {
  const total = Math.floor(ms / 1000);
  const d = Math.floor(total / 86400);
  const h = Math.floor((total % 86400) / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const hms = [h, m, s].map((n) => String(n).padStart(2, "0")).join(":");
  return d > 0 ? `${d}d ${hms}` : hms;
}

// --- Catalog helpers for choosing the round and the drivers ----------------------------------

export type SeasonRound = S["CalendarRound"];

export async function fetchSeasonYears(): Promise<number[]> {
  const page = await apiJson<{ results: { year: number }[] }>("/api/v1/seasons/?page_size=100");
  return page.results.map((s) => s.year).sort((a, b) => b - a);
}

export const fetchSeasonRounds = async (year: number): Promise<SeasonRound[]> =>
  (await apiJson<S["SeasonDetail"]>(`/api/v1/seasons/${year}/`)).rounds;

/** Rounds that still can be predicted: not cancelled and without a winner yet, in calendar order. */
export function upcomingRounds(rounds: SeasonRound[]): number[] {
  return rounds
    .filter((r) => r.round != null && !r.is_cancelled && r.winner == null)
    .map((r) => r.round as number)
    .sort((a, b) => a - b);
}

export type NextRound =
  | { kind: "round"; year: number; result: RoundStateResult }
  | { kind: "none"; year: number | null };

const MAX_ROUNDS_PROBED = 6;

/**
 * Finds the next round to predict: walks the upcoming rounds of the latest season and returns
 * the first one the server reports as open (else the first upcoming one, for the closed view).
 * Which rounds are "upcoming" comes from the calendar; whether a round is open is the server's call.
 */
export async function findNextRound(): Promise<NextRound> {
  const years = await fetchSeasonYears();
  const year = years[0];
  if (year === undefined) return { kind: "none", year: null };
  const candidates = upcomingRounds(await fetchSeasonRounds(year)).slice(0, MAX_ROUNDS_PROBED);
  let firstSeen: RoundStateResult | null = null;
  for (const n of candidates) {
    const result = await fetchRoundState(year, n);
    firstSeen ??= result;
    if (result.state.status === "open") return { kind: "round", year, result };
  }
  return firstSeen ? { kind: "round", year, result: firstSeen } : { kind: "none", year };
}

export type PickableDriver = { id: number; name: string; code: string | null; number: number | null };

/**
 * Drivers that can be picked for a season. The pick API takes numeric driver ids, so only entries
 * that carry an `id` are usable (see the note in the final report: the catalog does not expose it yet).
 */
export async function fetchPickableDrivers(year: number): Promise<PickableDriver[]> {
  const page = await apiJson<{ results: Array<S["DriverList"] & { id?: number }> }>(`/api/v1/drivers/?season=${year}&page_size=100&ordering=family_name`);
  return page.results
    .filter((d): d is S["DriverList"] & { id: number } => typeof d.id === "number")
    .map((d) => ({ id: d.id, name: `${d.given_name} ${d.family_name}`, code: d.code, number: d.number }));
}

// --- History, leaderboard, leagues ------------------------------------------------------------

export const fetchHistory = () => apiJson<HistoryRow[]>("/api/v1/predictions/history/");

export type LeaderboardParams = { season?: number; round?: number; league?: string; limit: number; offset: number };

export function fetchLeaderboard(p: LeaderboardParams): Promise<Leaderboard> {
  const q = new URLSearchParams();
  if (p.season) q.set("season", String(p.season));
  if (p.season && p.round) q.set("round", String(p.round));
  if (p.league) q.set("league", p.league);
  q.set("limit", String(p.limit));
  q.set("offset", String(p.offset));
  return apiJson<Leaderboard>(`/api/v1/predictions/leaderboard/?${q}`);
}

export const fetchLeagues = () => apiJson<LeagueSummary[]>("/api/v1/leagues/");
export const fetchLeague = (code: string) => apiJson<LeagueDetail>(`/api/v1/leagues/${encodeURIComponent(code)}/`);
export const createLeague = (name: string) => apiJson<LeagueDetail>("/api/v1/leagues/", { method: "POST", body: { name } });
export const joinLeague = (code: string) => apiJson<LeagueDetail>("/api/v1/leagues/join/", { method: "POST", body: { code } });
export const leaveLeague = (code: string) => apiRequest(`/api/v1/leagues/${encodeURIComponent(code)}/leave/`, { method: "POST" });
export const deleteLeague = (code: string) => apiRequest(`/api/v1/leagues/${encodeURIComponent(code)}/`, { method: "DELETE" });
export const renewLeagueCode = (code: string) => apiJson<LeagueDetail>(`/api/v1/leagues/${encodeURIComponent(code)}/renew-code/`, { method: "POST" });
export const removeLeagueMember = (code: string, userId: number) =>
  apiRequest(`/api/v1/leagues/${encodeURIComponent(code)}/members/${userId}/`, { method: "DELETE" });
export const fetchLeaguePicks = (code: string, year: number, round: number) =>
  apiJson<MemberPick[]>(`/api/v1/leagues/${encodeURIComponent(code)}/rounds/${year}/${round}/picks/`);

export const inviteLink = (code: string, origin: string) => `${origin}/leagues/join/${encodeURIComponent(code)}`;

/** Accepts a bare code or a full invite link and returns the code. */
export function parseInviteCode(input: string): string {
  const text = input.trim();
  const m = text.match(/\/leagues\/join\/([^/?#\s]+)/);
  return decodeURIComponent(m ? m[1] : text).toUpperCase();
}
