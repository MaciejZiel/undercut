import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { PickableDriver } from "@/lib/predict/api";
import { DriverCombobox, filterDrivers } from "./driver-combobox";

const drivers: PickableDriver[] = [
  { id: 1, name: "Max Verstappen", code: "VER", number: 1 },
  { id: 2, name: "Lando Norris", code: "NOR", number: 4 },
  { id: 3, name: "Sergio Pérez", code: "PER", number: 11 },
  { id: 4, name: "Oscar Piastri", code: "PIA", number: 81 },
];

function setup(props: Partial<React.ComponentProps<typeof DriverCombobox>> = {}) {
  const onChange = vi.fn();
  render(<DriverCombobox label="Winner (P1)" drivers={drivers} value={null} onChange={onChange} {...props} />);
  return { onChange, input: screen.getByRole("combobox", { name: "Winner (P1)" }) };
}

describe("driver combobox", () => {
  it("filters by name, code and ignores diacritics", () => {
    expect(filterDrivers(drivers, "perez").map((d) => d.id)).toEqual([3]);
    expect(filterDrivers(drivers, "nor").map((d) => d.id)).toEqual([2]);
    expect(filterDrivers(drivers, "81").map((d) => d.id)).toEqual([4]);
    expect(filterDrivers(drivers, "").length).toBe(4);
  });

  it("is operable with the keyboard only", () => {
    const { input, onChange } = setup();
    fireEvent.focus(input);
    expect(input).toHaveAttribute("aria-expanded", "true");
    expect(screen.getAllByRole("option")).toHaveLength(4);
    fireEvent.keyDown(input, { key: "ArrowDown" });
    expect(input.getAttribute("aria-activedescendant")).toBe(screen.getAllByRole("option")[1].id);
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onChange).toHaveBeenCalledWith(2);
    expect(input).toHaveAttribute("aria-expanded", "false");
  });

  it("filters while typing and selects the match with Enter", () => {
    const { input, onChange } = setup();
    fireEvent.change(input, { target: { value: "pia" } });
    expect(screen.getAllByRole("option")).toHaveLength(1);
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onChange).toHaveBeenCalledWith(4);
  });

  it("closes with Escape and wraps around with arrows, Home and End", () => {
    const { input } = setup();
    fireEvent.keyDown(input, { key: "ArrowDown" });
    expect(input).toHaveAttribute("aria-expanded", "true");
    fireEvent.keyDown(input, { key: "End" });
    expect(input.getAttribute("aria-activedescendant")).toBe(screen.getAllByRole("option")[3].id);
    fireEvent.keyDown(input, { key: "ArrowDown" });
    expect(input.getAttribute("aria-activedescendant")).toBe(screen.getAllByRole("option")[0].id);
    fireEvent.keyDown(input, { key: "Escape" });
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("skips and refuses drivers that are already on the podium", () => {
    const { input, onChange } = setup({ disabledIds: new Set([2]) });
    fireEvent.focus(input);
    const options = screen.getAllByRole("option");
    expect(options[1]).toHaveAttribute("aria-disabled", "true");
    fireEvent.click(options[1]);
    expect(onChange).not.toHaveBeenCalled();
    fireEvent.keyDown(input, { key: "ArrowDown" }); // from index 0 skips disabled index 1
    expect(input.getAttribute("aria-activedescendant")).toBe(options[2].id);
  });

  it("shows the selected driver when closed and an empty message when nothing matches", () => {
    const { input } = setup({ value: 1 });
    expect(input).toHaveValue("Max Verstappen (VER)");
    fireEvent.change(input, { target: { value: "zzz" } });
    expect(screen.getByText("No driver matches.")).toBeInTheDocument();
  });
});
