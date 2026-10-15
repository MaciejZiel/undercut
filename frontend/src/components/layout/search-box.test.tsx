import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

import { SearchBox } from "./search-box";

const payload = {
  drivers: Array.from({ length: 7 }, (_, i) => ({ slug: `d${i}`, name: `Driver ${i}`, code: null, number: null, nationality: "Finnish" })),
  constructors: [{ slug: "ferrari", name: "Ferrari", nationality: "Italian" }],
  circuits: [],
  rounds: [],
};

let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  push.mockReset();
  fetchMock = vi.fn(async () => Response.json(payload));
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

async function typeQuery(text: string) {
  const input = screen.getByRole("combobox");
  fireEvent.change(input, { target: { value: text } });
  await act(async () => {
    await vi.advanceTimersByTimeAsync(250);
  });
  return input;
}

describe("SearchBox", () => {
  it("does not call the API for fewer than 2 characters", async () => {
    render(<SearchBox />);
    await typeQuery("r");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("debounces and shows grouped suggestions, at most 5 per group", async () => {
    render(<SearchBox />);
    const input = screen.getByRole("combobox");
    fireEvent.change(input, { target: { value: "ra" } });
    fireEvent.change(input, { target: { value: "rai" } });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(250);
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const req = fetchMock.mock.calls[0][0] as Request;
    expect(new URL(req.url).searchParams.get("q")).toBe("rai");
    await waitFor(() => expect(screen.getAllByRole("option")).toHaveLength(6));
    expect(screen.getByRole("group", { name: "Drivers" })).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Constructors" })).toBeInTheDocument();
    expect(input).toHaveAttribute("aria-expanded", "true");
  });

  it("moves with arrow keys and opens the highlighted suggestion with Enter", async () => {
    render(<SearchBox />);
    const input = await typeQuery("rai");
    await waitFor(() => expect(screen.getAllByRole("option").length).toBeGreaterThan(0));
    fireEvent.keyDown(input, { key: "ArrowDown" });
    fireEvent.keyDown(input, { key: "ArrowDown" });
    const options = screen.getAllByRole("option");
    expect(options[1]).toHaveAttribute("aria-selected", "true");
    expect(input).toHaveAttribute("aria-activedescendant", options[1].id);
    fireEvent.keyDown(input, { key: "Enter" });
    expect(push).toHaveBeenCalledWith("/drivers/d1");
  });

  it("goes to the full results page on Enter without a highlighted suggestion", async () => {
    render(<SearchBox />);
    const input = await typeQuery("räikkönen");
    fireEvent.keyDown(input, { key: "Enter" });
    expect(push).toHaveBeenCalledWith("/search?q=r%C3%A4ikk%C3%B6nen");
  });

  it("closes on Escape", async () => {
    render(<SearchBox />);
    const input = await typeQuery("rai");
    await waitFor(() => expect(input).toHaveAttribute("aria-expanded", "true"));
    fireEvent.keyDown(input, { key: "Escape" });
    expect(input).toHaveAttribute("aria-expanded", "false");
  });

  it("focuses the input when / is pressed outside a field", () => {
    render(<SearchBox />);
    const input = screen.getByRole("combobox");
    // jsdom has no layout: pretend the input is visible.
    input.getClientRects = () => [{}] as unknown as DOMRectList;
    fireEvent.keyDown(document.body, { key: "/" });
    expect(input).toHaveFocus();
  });

  it("does not steal / while typing in another field", () => {
    render(
      <>
        <textarea aria-label="notes" />
        <SearchBox />
      </>,
    );
    const input = screen.getByRole("combobox");
    input.getClientRects = () => [{}] as unknown as DOMRectList;
    fireEvent.keyDown(screen.getByLabelText("notes"), { key: "/" });
    expect(input).not.toHaveFocus();
  });

  it("shows an error message when the API fails", async () => {
    fetchMock.mockResolvedValueOnce(new Response("boom", { status: 500 }));
    render(<SearchBox />);
    await typeQuery("rai");
    expect(await screen.findByText("Search is unavailable right now.")).toBeInTheDocument();
  });
});
