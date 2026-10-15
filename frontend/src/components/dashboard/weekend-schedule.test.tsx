import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { mockFetch } from "@/test/fetch-mock";
import { ME_USER, renderWithProviders } from "@/test/render";
import { WeekendSchedule, relativeLabel } from "./weekend-schedule";

const HOUR = 3_600_000;

describe("relativeLabel", () => {
  const start = Date.parse("2026-10-23T17:30:00Z");
  const end = start + HOUR;
  it("says nothing until the clock exists", () => {
    expect(relativeLabel(start, end, null)).toBe("");
  });
  it("counts down in days, hours and minutes", () => {
    expect(relativeLabel(start, end, start - 5 * 24 * HOUR)).toBe("in 5 days");
    expect(relativeLabel(start, end, start - 5 * HOUR - 1000)).toBe("in 5 h");
    expect(relativeLabel(start, end, start - 20 * 60_000)).toBe("in 20 min");
    expect(relativeLabel(start, end, start - 1000)).toBe("in 1 min");
  });
  it("knows when a session is on and when it is over", () => {
    expect(relativeLabel(start, end, start + 10 * 60_000)).toBe("on now");
    expect(relativeLabel(start, end, end + 1)).toBe("done");
    expect(relativeLabel(start, null, start + HOUR)).toBe("on now");
  });
});

describe("WeekendSchedule", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });
  const sessions = [
    { type: "RACE", start_utc: "2026-10-25T20:00:00Z", end_utc: "2026-10-25T22:00:00Z", status: "scheduled" },
    { type: "FP1", start_utc: "2026-10-23T17:30:00Z", end_utc: "2026-10-23T18:30:00Z", status: "scheduled" },
    { type: "Q", start_utc: null, end_utc: null, status: "scheduled" },
  ];

  it("lists sessions in time order in the viewer's zone and leaves out sessions without a time", async () => {
    mockFetch({ "GET /api/v1/auth/me/": { body: ME_USER } }); // the saved zone is Europe/Warsaw
    renderWithProviders(<WeekendSchedule sessions={sessions} />);
    const rows = await screen.findAllByRole("row");
    expect(rows).toHaveLength(2);
    expect(rows[0]).toHaveTextContent("Practice 1");
    expect(rows[1]).toHaveTextContent("Race");
    expect(await screen.findByRole("table", { name: /Europe\/Warsaw/ })).toBeInTheDocument();
    expect(rows[1]).toHaveTextContent("21:00"); // 20:00 UTC; Warsaw is back on UTC+1 from 25 October
  });

  it("renders nothing without any timed session", () => {
    mockFetch({ "GET /api/v1/auth/me/": { body: ME_USER } });
    const { container } = renderWithProviders(<WeekendSchedule sessions={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
