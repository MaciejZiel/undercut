import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

let mockPath = "/";
vi.mock("next/navigation", () => ({ usePathname: () => mockPath }));

import { MainNav } from "./main-nav";
import { MobileTabBar } from "./mobile-tab-bar";
import { SiteFooter } from "./site-footer";

const LABELS = ["Dashboard", "Calendar", "Standings", "Catalog", "Predict"];

describe("main navigation", () => {
  it("renders the 5 items, Catalog as a dropdown button", () => {
    mockPath = "/";
    render(<MainNav />);
    const nav = screen.getByRole("navigation", { name: "Main" });
    for (const label of LABELS) {
      expect(within(nav).getByText(label)).toBeInTheDocument();
    }
    expect(within(nav).getByRole("button", { name: "Catalog" })).toHaveAttribute("aria-expanded", "false");
    expect(within(nav).getByRole("link", { name: "Dashboard" })).toHaveAttribute("aria-current", "page");
  });

  it("opens the catalog dropdown by click and closes it with Escape", () => {
    mockPath = "/calendar";
    render(<MainNav />);
    const button = screen.getByRole("button", { name: "Catalog" });
    fireEvent.click(button);
    expect(button).toHaveAttribute("aria-expanded", "true");
    for (const l of ["Drivers", "Constructors", "Circuits", "Seasons"]) {
      expect(screen.getByRole("link", { name: new RegExp(l) })).toBeVisible();
    }
    fireEvent.keyDown(button, { key: "Escape" });
    expect(button).toHaveAttribute("aria-expanded", "false");
    expect(button).toHaveFocus();
  });

  it("marks Catalog as current on a catalog sub-route", () => {
    mockPath = "/drivers/hamilton";
    render(<MainNav />);
    expect(screen.getByRole("button", { name: "Catalog" })).toHaveAttribute("aria-current", "true");
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
    expect(within(bar).getByRole("link", { name: "Catalog" })).toHaveAttribute("href", "/catalog");
  });
});

describe("footer", () => {
  it("shows the exact disclaimer", () => {
    render(<SiteFooter />);
    expect(
      screen.getByText(
        "Unofficial fan site. Not affiliated with Formula One Group or the FIA. Data: Jolpica-F1, OpenF1.",
      ),
    ).toBeInTheDocument();
  });
});

