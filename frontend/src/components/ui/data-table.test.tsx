import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DataTable, RowTh, SortTh, Td, Th, Tr } from "./data-table";
import { Dash, orDash } from "./value";
import { Pagination } from "./pagination";
import { StatTiles } from "./stat-tiles";

function Table({ ordering }: { ordering: string }) {
  return (
    <DataTable caption="Drivers">
      <thead>
        <tr>
          <SortTh label="Driver" field="family_name" ordering={ordering} path="/drivers" params={{ season: 1988, page: 3 }} />
          <SortTh label="Wins" field="wins" numeric ordering={ordering} path="/drivers" params={{ season: 1988, page: 3 }} />
          <Th>Team</Th>
        </tr>
      </thead>
      <tbody>
        <Tr>
          <RowTh>Ayrton Senna</RowTh>
          <Td>{orDash(41)}</Td>
          <Td>{orDash(null)}</Td>
        </Tr>
      </tbody>
    </DataTable>
  );
}

describe("DataTable", () => {
  it("has a caption and column/row headers", () => {
    render(<Table ordering="family_name" />);
    expect(screen.getByRole("table", { name: "Drivers" })).toBeInTheDocument();
    expect(screen.getAllByRole("columnheader")).toHaveLength(3);
    expect(screen.getByRole("rowheader", { name: "Ayrton Senna" })).toBeInTheDocument();
  });

  it("marks the sorted column with aria-sort and the others as none", () => {
    render(<Table ordering="-wins" />);
    expect(screen.getByRole("columnheader", { name: /Wins/ })).toHaveAttribute("aria-sort", "descending");
    expect(screen.getByRole("columnheader", { name: /Driver/ })).toHaveAttribute("aria-sort", "none");
    expect(screen.getByRole("columnheader", { name: "Team" })).not.toHaveAttribute("aria-sort");
  });

  it("links sort headers through the URL, keeping filters and resetting the page", () => {
    render(<Table ordering="family_name" />);
    const wins = within(screen.getByRole("columnheader", { name: /Wins/ })).getByRole("link");
    expect(wins).toHaveAttribute("href", "/drivers?season=1988&ordering=-wins");
    const name = within(screen.getByRole("columnheader", { name: /Driver/ })).getByRole("link");
    expect(name).toHaveAttribute("href", "/drivers?season=1988&ordering=-family_name");
  });
});

describe("null rendering", () => {
  it("renders an em dash with a tooltip, not zero", () => {
    render(<Table ordering="family_name" />);
    const dash = screen.getByTitle("No data");
    expect(dash).toHaveTextContent("—");
    expect(dash).not.toHaveTextContent("0");
  });

  it("keeps a real zero", () => {
    render(<span data-testid="v">{orDash(0)}</span>);
    expect(screen.getByTestId("v")).toHaveTextContent("0");
  });

  it("accepts a custom tooltip", () => {
    render(<Dash label="Not available yet" />);
    expect(screen.getByTitle("Not available yet")).toBeInTheDocument();
  });

  it("stat tiles show a dash for null", () => {
    render(<StatTiles stats={[{ label: "Titles", value: null }, { label: "Wins", value: "0" }]} />);
    expect(screen.getByTitle("No data")).toBeInTheDocument();
    expect(screen.getByText("Wins").nextSibling).toHaveTextContent("0");
  });
});

describe("Pagination", () => {
  it("renders nothing for a single page", () => {
    const { container } = render(<Pagination path="/drivers" params={{}} page={1} pageSize={25} count={10} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("links to neighbouring pages and keeps filters", () => {
    render(<Pagination path="/drivers" params={{ season: 1988 }} page={2} pageSize={25} count={60} />);
    expect(screen.getByRole("link", { name: "Previous" })).toHaveAttribute("href", "/drivers?season=1988");
    expect(screen.getByRole("link", { name: "Next" })).toHaveAttribute("href", "/drivers?season=1988&page=3");
    expect(screen.getByText("26–50 of 60")).toBeInTheDocument();
  });

  it("disables previous on the first page", () => {
    render(<Pagination path="/drivers" params={{}} page={1} pageSize={25} count={60} />);
    expect(screen.queryByRole("link", { name: "Previous" })).toBeNull();
    expect(screen.getByText("Previous")).toHaveAttribute("aria-disabled", "true");
  });
});
