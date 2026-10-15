import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { mockFetch } from "@/test/fetch-mock";
import { ME_ANON, ME_USER, renderWithProviders } from "@/test/render";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));

import { LeaderboardPanel } from "./leaderboard";

const row = (rank: number, user_id: number, name: string, points: number) => ({ rank, user_id, name, points, exact_hits: 1, pole_hits: 0, exact_podiums: 0, predictions: 3 });
const board = { season: null, round: null, count: 3, results: [row(1, 1, "Alice", 50), row(2, 2, "Bob", 40), row(3, 7, "Max Fan", 10)] };

let observers: { cb: IntersectionObserverCallback }[] = [];
class FakeIO {
  constructor(public cb: IntersectionObserverCallback) {
    observers.push({ cb });
  }
  observe() {}
  disconnect() {}
}

afterEach(() => {
  vi.unstubAllGlobals();
  observers = [];
});

describe("leaderboard", () => {
  it("renders the table for visitors (public) with no pinned row", async () => {
    mockFetch({ "GET /api/v1/auth/me/": { body: ME_ANON }, "GET /api/v1/predictions/leaderboard/": { body: board }, "GET /api/v1/seasons/": { body: { results: [{ year: 2026 }, { year: 2025 }] } } });
    renderWithProviders(<LeaderboardPanel />);
    expect(await screen.findByText("Alice")).toBeInTheDocument();
    expect(screen.queryByTestId("pinned-own-row")).not.toBeInTheDocument();
  });

  it("applies the season and round filters to the query", async () => {
    const m = mockFetch({
      "GET /api/v1/auth/me/": { body: ME_ANON },
      "GET /api/v1/predictions/leaderboard/": { body: board },
      "GET /api/v1/seasons/": { body: { results: [{ year: 2026 }, { year: 2025 }] } },
      "GET /api/v1/seasons/2026/": { body: { rounds: [{ round: 1, name: "Australia", is_cancelled: false, winner: null }] } },
    });
    renderWithProviders(<LeaderboardPanel />);
    await screen.findByText("Alice");
    await screen.findByRole("option", { name: "2026" });
    fireEvent.change(screen.getByLabelText("Season"), { target: { value: "2026" } });
    await screen.findByRole("option", { name: "1. Australia" });
    fireEvent.change(screen.getByLabelText("Round"), { target: { value: "1" } });
    await waitFor(() => expect(m.calls.some((c) => c.url.includes("season=2026") && c.url.includes("round=1") && c.url.includes("offset=0"))).toBe(true));
  });

  it("pins the own row at the bottom only while it is off-screen", async () => {
    vi.stubGlobal("IntersectionObserver", FakeIO);
    mockFetch({ "GET /api/v1/auth/me/": { body: ME_USER }, "GET /api/v1/predictions/leaderboard/": { body: board } });
    renderWithProviders(<LeaderboardPanel />);
    await screen.findByText("Alice");
    await waitFor(() => expect(observers.length).toBeGreaterThan(0));
    const fire = (isIntersecting: boolean) => observers.at(-1)!.cb([{ isIntersecting } as IntersectionObserverEntry], {} as IntersectionObserver);
    fire(false);
    expect(await screen.findByTestId("pinned-own-row")).toHaveTextContent("#3");
    fire(true);
    await waitFor(() => expect(screen.queryByTestId("pinned-own-row")).not.toBeInTheDocument());
  });

  it("shows the empty state", async () => {
    mockFetch({ "GET /api/v1/auth/me/": { body: ME_ANON }, "GET /api/v1/predictions/leaderboard/": { body: { season: null, round: null, count: 0, results: [] } }, "GET /api/v1/seasons/": { body: { results: [] } } });
    renderWithProviders(<LeaderboardPanel />);
    expect(await screen.findByText("No scores yet")).toBeInTheDocument();
  });

  it("shows an error state with retry", async () => {
    mockFetch({ "GET /api/v1/auth/me/": { body: ME_ANON }, "GET /api/v1/predictions/leaderboard/": { status: 500, body: {} }, "GET /api/v1/seasons/": { body: { results: [] } } });
    renderWithProviders(<LeaderboardPanel />);
    expect(await screen.findByRole("button", { name: "Try again" })).toBeInTheDocument();
  });
});
