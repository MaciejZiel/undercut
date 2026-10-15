import { fireEvent, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { components } from "@/lib/api/client";
import { mockFetch } from "@/test/fetch-mock";
import { ME_ANON, ME_USER, renderWithProviders } from "@/test/render";
import { CalendarView } from "./calendar-view";
import { formatSessionTime, icsHref, safeZone, sessionLabel, statusLabel } from "./time";

type Entry = components["schemas"]["CalendarEntry"];

const entry = (over: Partial<Entry>): Entry => ({
  round: 1,
  name: "Test Grand Prix",
  date: "2099-03-15",
  status: "upcoming",
  is_next: false,
  has_sprint: false,
  race_start_utc: "2099-03-15T15:00:00Z",
  circuit: { slug: "test", name: "Test Circuit", country: "Japan", locality: "Suzuka", timezone: "Asia/Tokyo" },
  sessions: [
    { type: "FP1", start_utc: "2099-03-13T02:30:00Z", end_utc: null, status: "scheduled" },
    { type: "RACE", start_utc: "2099-03-15T15:00:00Z", end_utc: null, status: "scheduled" },
  ],
  winner: null,
  ...over,
});

describe("time helpers", () => {
  it("formats an instant in a zone and rejects bad input", () => {
    expect(formatSessionTime("2099-03-15T15:00:00Z", "Asia/Tokyo")).toContain("00:00");
    expect(formatSessionTime("2099-03-15T15:00:00Z", "Not/AZone")).toContain("15:00");
    expect(formatSessionTime(null, "UTC")).toBeNull();
    expect(formatSessionTime("garbage", "UTC")).toBeNull();
  });
  it("validates zones, labels and builds the ics link", () => {
    expect(safeZone("Europe/Warsaw")).toBe("Europe/Warsaw");
    expect(safeZone("nope")).toBeNull();
    expect(safeZone(null)).toBeNull();
    expect(sessionLabel("SQ")).toBe("Sprint qualifying");
    expect(statusLabel("cancelled")).toBe("Cancelled");
    expect(icsHref(2025, 3)).toBe("/api/v1/calendar/ics/?year=2025&round=3");
    expect(icsHref(2025)).toBe("/api/v1/calendar/ics/?year=2025");
  });
});

describe("CalendarView", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("labels statuses, highlights the next round and keeps cancelled rounds", () => {
    mockFetch({ "GET /api/v1/auth/me/": { body: ME_ANON } });
    renderWithProviders(
      <CalendarView
        year={2099}
        rounds={[
          entry({ round: 1, name: "Done GP", status: "completed" }),
          entry({ round: 2, name: "Next GP", status: "next", is_next: true }),
          entry({ round: 3, name: "Later GP", status: "upcoming" }),
          entry({ round: 4, name: "Gone GP", status: "cancelled", sessions: [] }),
        ]}
      />,
    );
    const articles = screen.getAllByRole("article");
    expect(articles).toHaveLength(4);
    expect(within(articles[0]).getByText("Completed")).toBeInTheDocument();
    expect(articles[1]).toHaveAttribute("aria-current", "step");
    expect(within(articles[1]).getByRole("timer")).toBeInTheDocument();
    expect(within(articles[2]).getByText("Upcoming")).toBeInTheDocument();
    expect(within(articles[3]).getByText("Cancelled")).toBeInTheDocument();
    expect(within(articles[3]).queryByRole("link", { name: /Add to calendar/ })).not.toBeInTheDocument();
  });

  it("links 'Add to calendar' to the ics endpoint as a plain link", () => {
    mockFetch({ "GET /api/v1/auth/me/": { body: ME_ANON } });
    renderWithProviders(<CalendarView year={2099} rounds={[entry({ round: 7 })]} />);
    const link = screen.getByRole("link", { name: /Add to calendar/ });
    expect(link).toHaveAttribute("href", "/api/v1/calendar/ics/?year=2099&round=7");
    expect(link).not.toHaveAttribute("download");
  });

  it("uses the account time zone and toggles to circuit local time", async () => {
    mockFetch({ "GET /api/v1/auth/me/": { body: ME_USER } }); // timezone Europe/Warsaw
    renderWithProviders(<CalendarView year={2099} rounds={[entry({})]} />);
    expect(await screen.findByText("Times shown in Europe/Warsaw.")).toBeInTheDocument();
    expect(screen.getAllByText(/16:00/).length).toBeGreaterThan(0); // 15:00Z in Warsaw (CET, DST starts later in March)
    fireEvent.click(screen.getByRole("button", { name: "Circuit local time" }));
    expect(screen.getByRole("button", { name: "Circuit local time" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getAllByText(/00:00/).length).toBeGreaterThan(0); // Tokyo is UTC+9
  });

  it("falls back to the viewer zone when the circuit zone is unknown", () => {
    mockFetch({ "GET /api/v1/auth/me/": { body: ME_ANON } });
    renderWithProviders(
      <CalendarView year={2099} rounds={[entry({ circuit: { slug: "x", name: "X", country: null, locality: null, timezone: null } })]} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Circuit local time" }));
    expect(screen.getByText(/Circuit time zone unknown/)).toBeInTheDocument();
  });

  it("shows a dash for sessions without a start time", () => {
    mockFetch({ "GET /api/v1/auth/me/": { body: ME_ANON } });
    renderWithProviders(
      <CalendarView year={2099} rounds={[entry({ sessions: [{ type: "RACE", start_utc: null, end_utc: null, status: "scheduled" }] })]} />,
    );
    expect(screen.getByText("Time to be confirmed")).toBeInTheDocument();
  });
});
