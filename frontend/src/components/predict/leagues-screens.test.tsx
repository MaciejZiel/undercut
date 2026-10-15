import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mockFetch } from "@/test/fetch-mock";
import { ME_ANON, ME_USER, renderWithProviders } from "@/test/render";

const replace = vi.fn();
const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace, push }), usePathname: () => "/leagues" }));

import { RequireAuth } from "@/components/account/require-auth";
import { PredictHome } from "./round-screens";
import { LeagueScreen, LeaguesScreen } from "./leagues-screens";

const detail = (over: Record<string, unknown> = {}) => ({
  name: "Pit Wall",
  invite_code: "ABC123",
  owner_id: 7,
  is_owner: true,
  member_count: 2,
  max_members: 50,
  members: [
    { user_id: 7, name: "Max Fan", joined_at: "2026-01-01T00:00:00Z" },
    { user_id: 8, name: "Sam", joined_at: "2026-01-02T00:00:00Z" },
  ],
  ...over,
});
const emptyBoard = { season: null, round: null, count: 0, results: [] };

beforeEach(() => {
  replace.mockReset();
  push.mockReset();
  document.cookie = "csrftoken=t; path=/";
});
afterEach(() => vi.unstubAllGlobals());

describe("auth gate", () => {
  it("redirects visitors to /login keeping the target", async () => {
    window.history.pushState({}, "", "/predict/2026/3?x=1");
    mockFetch({ "GET /api/v1/auth/me/": { body: ME_ANON } });
    renderWithProviders(<RequireAuth>secret</RequireAuth>);
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/login?next=%2Fpredict%2F2026%2F3%3Fx%3D1"));
    expect(screen.queryByText("secret")).not.toBeInTheDocument();
  });

  it("shows what leagues are, with a sign-in link, when the session ended", async () => {
    window.history.pushState({}, "", "/leagues");
    let signedIn = true;
    mockFetch({
      "GET /api/v1/auth/me/": () => ({ body: signedIn ? ME_USER : ME_ANON }),
      "GET /api/v1/leagues/": () => {
        signedIn = false;
        return { status: 401, body: { detail: "Authentication credentials were not provided." } };
      },
    });
    renderWithProviders(<LeaguesScreen />);
    expect(await screen.findByText("Play against your friends")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute("href", expect.stringContaining("/login?next="));
    expect(replace).not.toHaveBeenCalled();
  });
});

describe("leagues", () => {
  it("creates a league and opens it", async () => {
    const m = mockFetch({
      "GET /api/v1/auth/me/": { body: ME_USER },
      "GET /api/v1/leagues/": { body: [] },
      "POST /api/v1/leagues/": { status: 201, body: detail() },
    });
    renderWithProviders(<LeaguesScreen />);
    expect(await screen.findByText("No leagues yet")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("League name"), { target: { value: "Pit Wall" } });
    fireEvent.click(screen.getByRole("button", { name: "Create league" }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/leagues/ABC123"));
    expect(m.calls.find((c) => c.method === "POST")!.body).toEqual({ name: "Pit Wall" });
  });

  it("joins by pasted invite link and shows the API error", async () => {
    const m = mockFetch({
      "GET /api/v1/auth/me/": { body: ME_USER },
      "GET /api/v1/leagues/": { body: [] },
      "POST /api/v1/leagues/join/": { status: 409, body: { detail: "full", code: "league_full" } },
    });
    renderWithProviders(<LeaguesScreen />);
    await screen.findByText("No leagues yet");
    fireEvent.change(screen.getByLabelText("Invite code or link"), { target: { value: "https://x.test/leagues/join/abc123" } });
    fireEvent.click(screen.getByRole("button", { name: "Join league" }));
    expect(await screen.findByText("This league is full.")).toBeInTheDocument();
    expect(m.calls.find((c) => c.method === "POST")!.body).toEqual({ code: "ABC123" });
  });

  const leagueRoutes = (d = detail()) => ({
    "GET /api/v1/auth/me/": { body: ME_USER },
    "GET /api/v1/leagues/ABC123/": { body: d },
    "GET /api/v1/predictions/leaderboard/": { body: emptyBoard },
    "GET /api/v1/seasons/": { body: { results: [{ year: 2026 }] } },
    "GET /api/v1/seasons/2026/": { body: { rounds: [{ round: 4, name: "Miami", is_cancelled: false, winner: null }] } },
  });

  it("copies the invite link", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    mockFetch({ ...leagueRoutes(), "GET /api/v1/leagues/ABC123/rounds/2026/4/picks/": { body: [] } });
    renderWithProviders(<LeagueScreen code="ABC123" />);
    fireEvent.click(await screen.findByRole("button", { name: "Copy invite link" }));
    await waitFor(() => expect(writeText).toHaveBeenCalledWith(`${window.location.origin}/leagues/join/ABC123`));
    expect(await screen.findByText("Invite link copied.")).toBeInTheDocument();
  });

  it("lets the owner remove a member and delete the league, after confirmation", async () => {
    const m = mockFetch({
      ...leagueRoutes(),
      "GET /api/v1/leagues/ABC123/rounds/2026/4/picks/": { body: [] },
      "DELETE /api/v1/leagues/ABC123/members/8/": { status: 204 },
      "DELETE /api/v1/leagues/ABC123/": { status: 204 },
    });
    renderWithProviders(<LeagueScreen code="ABC123" />);
    fireEvent.click(await screen.findByRole("button", { name: "Remove Sam from the league" }));
    fireEvent.click(screen.getByRole("button", { name: "Remove" }));
    await waitFor(() => expect(m.calls.some((c) => c.method === "DELETE" && c.url.endsWith("/members/8/"))).toBe(true));
    fireEvent.click(screen.getByRole("button", { name: "Delete league" }));
    const dialog = await screen.findByRole("dialog", { name: "Delete this league?" });
    expect(m.calls.some((c) => c.method === "DELETE" && c.url === "/api/v1/leagues/ABC123/")).toBe(false);
    fireEvent.click(within(dialog).getByRole("button", { name: "Delete league" }));
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/leagues"));
  });

  it("offers members Leave instead of owner actions", async () => {
    mockFetch({ ...leagueRoutes(detail({ is_owner: false, owner_id: 8 })), "GET /api/v1/leagues/ABC123/rounds/2026/4/picks/": { body: [] } });
    renderWithProviders(<LeagueScreen code="ABC123" />);
    expect(await screen.findByRole("button", { name: "Leave league" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Renew invite code" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Remove .* from the league/ })).not.toBeInTheDocument();
  });

  it("explains that other picks are hidden until the lock (403)", async () => {
    mockFetch({
      ...leagueRoutes(),
      "GET /api/v1/leagues/ABC123/rounds/2026/4/picks/": { status: 403, body: { detail: "hidden", code: "picks_hidden" } },
    });
    renderWithProviders(<LeagueScreen code="ABC123" />);
    expect(await screen.findByText("Picks are hidden for now")).toBeInTheDocument();
    expect(screen.getByText("Other players' picks are visible after predictions close.")).toBeInTheDocument();
  });

  it("shows a 404 league as an error state, not a crash", async () => {
    mockFetch({ "GET /api/v1/auth/me/": { body: ME_USER }, "GET /api/v1/leagues/NOPE/": { status: 404, body: { detail: "League not found.", code: "league_not_found" } } });
    renderWithProviders(<LeagueScreen code="NOPE" />);
    expect(await screen.findByRole("alert")).toHaveTextContent("League not found.");
  });
});

describe("predict home", () => {
  it("lets visitors see the next round and open its form", async () => {
    mockFetch({
      "GET /api/v1/auth/me/": { body: ME_ANON },
      "GET /api/v1/seasons/": { body: { results: [{ year: 2026 }] } },
      "GET /api/v1/seasons/2026/": { body: { rounds: [{ round: 3, name: "Australia", is_cancelled: false, winner: null }] } },
      "GET /api/v1/predictions/rounds/2026/3/": {
        body: { round: { id: 3, year: 2026, round: 3, name: "Australian Grand Prix" }, status: "open", closes_at: new Date(Date.now() + 86_400_000 * 2).toISOString(), my_pick: null },
        headers: { Date: new Date().toUTCString() },
      },
    });
    renderWithProviders(<PredictHome />);
    expect(await screen.findByRole("heading", { name: "Australian Grand Prix" })).toBeInTheDocument();
    expect(screen.getByLabelText(/Predictions close in/)).toBeInTheDocument();
    const link = await screen.findByRole("link", { name: "Predict the podium" });
    expect(link).toHaveAttribute("href", "/predict/2026/3");
  });
});
