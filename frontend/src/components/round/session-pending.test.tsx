import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SessionPending } from "./session-pending";

const props = { label: "Race", backHref: "/seasons/2026", backLabel: "Back" };

describe("SessionPending", () => {
  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });
  function at(now: string, start: string | null) {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(now));
    render(<SessionPending {...props} startUtc={start} />);
    act(() => {
      vi.advanceTimersByTime(1000);
    });
  }

  it("counts down before the session", () => {
    at("2026-10-01T10:00:00Z", "2026-10-04T08:00:00Z");
    expect(screen.getByText("Race starts in")).toBeInTheDocument();
    expect(screen.getByRole("timer")).toBeInTheDocument();
  });
  it("says results are on their way shortly after the session", () => {
    at("2026-10-04T12:00:00Z", "2026-10-04T08:00:00Z");
    expect(screen.getByText("Results are on their way")).toBeInTheDocument();
  });
  it("admits missing data a day later and offers a report link", () => {
    at("2026-10-06T12:00:00Z", "2026-10-04T08:00:00Z");
    expect(screen.getByText("We do not have this result yet")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Report it on GitHub" })).toHaveAttribute("href", expect.stringContaining("github.com"));
  });
  it("handles an unknown start time", () => {
    at("2026-10-06T12:00:00Z", null);
    expect(screen.getByText("Race time to be confirmed")).toBeInTheDocument();
  });
});
