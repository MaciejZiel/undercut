import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DriversTable } from "./driver-tables";
import { CalendarTable } from "./season-tables";

describe("DriversTable", () => {
  const driver = {
    slug: "ayrton_senna",
    given_name: "Ayrton",
    family_name: "Senna",
    code: null,
    number: null,
    nationality: "Brazilian",
    starts: 161,
    wins: 41,
    titles: null,
    team: { slug: "mclaren", name: "McLaren", color: null },
  };

  it("links the driver and team, shows a flag, and dashes for null titles and number", () => {
    render(<DriversTable drivers={[driver]} ordering="wins" params={{}} />);
    expect(screen.getByRole("link", { name: "Ayrton Senna" })).toHaveAttribute("href", "/drivers/ayrton_senna");
    expect(screen.getByRole("link", { name: "McLaren" })).toHaveAttribute("href", "/constructors/mclaren");
    expect(screen.getByText("🇧🇷")).toBeInTheDocument();
    expect(screen.getByTitle("Not available yet")).toHaveTextContent("—");
    expect(screen.getByRole("columnheader", { name: /Wins/ })).toHaveAttribute("aria-sort", "ascending");
  });
});

describe("CalendarTable", () => {
  const circuit = { slug: "monza", name: "Monza", country: "Italy" };
  const rounds = [
    {
      round: 1,
      name: "Bahrain Grand Prix",
      date: "2024-03-02",
      is_cancelled: false,
      has_sprint: false,
      circuit,
      winner: { driver: { slug: "max", name: "Max Verstappen", code: null, number: null }, team: { slug: "rb", name: "Red Bull", color: null } },
    },
    { round: null, name: "Chinese Grand Prix", date: "2024-04-21", is_cancelled: true, has_sprint: false, circuit, winner: null },
    { round: 3, name: "Future Grand Prix", date: "2999-01-01", is_cancelled: false, has_sprint: true, circuit, winner: null },
  ];

  it("links rounds with winners, labels cancelled rounds and upcoming ones", () => {
    render(<CalendarTable year={2024} rounds={rounds} today="2024-06-01" />);
    expect(screen.getByRole("table", { name: "2024 calendar" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Bahrain Grand Prix" })).toHaveAttribute("href", "/seasons/2024/1");
    expect(screen.getByRole("link", { name: "Max Verstappen" })).toHaveAttribute("href", "/drivers/max");
    const cancelled = within(screen.getByText("Chinese Grand Prix").closest("tr")!);
    expect(cancelled.getByText("Cancelled")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Chinese Grand Prix" })).toBeNull();
    expect(screen.getByText("Upcoming")).toBeInTheDocument();
    expect(screen.getByText("Sprint")).toBeInTheDocument();
  });
});
