import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

let mockPath = "/";
vi.mock("next/navigation", () => ({ usePathname: () => mockPath }));

import { MainNav } from "./main-nav";
import { MobileTabBar } from "./mobile-tab-bar";
import { SiteFooter } from "./site-footer";

const LABELS = ["Weekend", "Calendar", "Standings", "Archive", "Predict"];

describe("main navigation", () => {
  it("renders the 5 groups, the ones with sub-pages as dropdown buttons", () => {
    mockPath = "/";
    render(<MainNav />);
    const nav = screen.getByRole("navigation", { name: "Main" });
    for (const label of LABELS) {
      expect(within(nav).getByText(label)).toBeInTheDocument();
    }
    for (const group of ["Standings", "Archive", "Predict"]) {
      expect(within(nav).getByRole("button", { name: group })).toHaveAttribute("aria-expanded", "false");
    }
    expect(within(nav).getByRole("link", { name: "Weekend" })).toHaveAttribute("aria-current", "page");
  });

  it("opens the archive dropdown by click and closes it with Escape", () => {
    mockPath = "/calendar";
    render(<MainNav />);
    const button = screen.getByRole("button", { name: "Archive" });
    fireEvent.click(button);
    expect(button).toHaveAttribute("aria-expanded", "true");
    for (const l of ["Drivers", "Constructors", "Circuits", "Seasons", "Compare drivers"]) {
      expect(screen.getByRole("link", { name: new RegExp(l) })).toBeVisible();
    }
    fireEvent.keyDown(button, { key: "Escape" });
    expect(button).toHaveAttribute("aria-expanded", "false");
    expect(button).toHaveFocus();
  });

  it("marks the archive as current on an archive sub-route", () => {
    mockPath = "/drivers/hamilton";
    render(<MainNav />);
    expect(screen.getByRole("button", { name: "Archive" })).toHaveAttribute("aria-current", "true");
  });

  it("lists the prediction pages, leagues included, under Predict", () => {
    mockPath = "/leagues";
    render(<MainNav />);
    const button = screen.getByRole("button", { name: "Predict" });
    expect(button).toHaveAttribute("aria-current", "true");
    fireEvent.click(button);
    expect(screen.getByRole("link", { name: /Leagues/ })).toHaveAttribute("href", "/leagues");
    expect(screen.getByRole("link", { name: /Leaderboard/ })).toHaveAttribute("href", "/predict/leaderboard");
  });
});

describe("mobile tab bar", () => {
  it("has the same 5 items and is hidden from md up", () => {
    mockPath = "/standings/drivers";
    render(<MobileTabBar />);
    const bar = screen.getByTestId("mobile-tab-bar");
    expect(bar.className).toContain("md:hidden");
    expect(bar.className).toContain("fixed");
    const links = within(bar).getAllByRole("link");
    expect(links.map((l) => l.textContent)).toEqual(LABELS);
    expect(within(bar).getByRole("link", { name: "Standings" })).toHaveAttribute("aria-current", "page");
    expect(within(bar).getByRole("link", { name: "Archive" })).toHaveAttribute("href", "/catalog");
  });
});

describe("footer", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shows the exact disclaimer", () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("{}", { status: 500 })));
    render(<SiteFooter />);
    expect(
      screen.getByText(
        "Unofficial fan site. Not affiliated with Formula One Group or the FIA. Data: Jolpica-F1, OpenF1.",
      ),
    ).toBeInTheDocument();
  });
});
