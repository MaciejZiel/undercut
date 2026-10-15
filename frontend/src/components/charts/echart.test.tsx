import { render, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const instance = { setOption: vi.fn(), resize: vi.fn(), dispose: vi.fn() };
const init = vi.fn(() => instance);
vi.mock("./echarts-setup", () => ({ echarts: { init } }));

import { EChart } from "./echart";
import { readChartTokens, seriesColor } from "./tokens";

describe("EChart", () => {
  it("initialises with the canvas renderer, applies the option and disposes on unmount", async () => {
    const option = vi.fn(() => ({ series: [] }));
    const { unmount, getByRole } = render(<EChart option={option} label="Test chart" />);
    expect(getByRole("img", { name: "Test chart" })).toBeInTheDocument();
    await waitFor(() => expect(instance.setOption).toHaveBeenCalled());
    expect(init).toHaveBeenCalledWith(expect.anything(), undefined, { renderer: "canvas" });
    expect(option).toHaveBeenCalledWith(expect.objectContaining({ fg: expect.any(String) }));
    unmount();
    expect(instance.dispose).toHaveBeenCalledTimes(1);
  });
});

describe("chart tokens", () => {
  it("reads CSS variables and wraps palette indexes", () => {
    document.documentElement.style.setProperty("--fg", "#123456");
    const t = readChartTokens();
    expect(t.fg).toBe("#123456");
    expect(seriesColor(t, 0)).toBe(seriesColor(t, t.palette.length));
    expect(seriesColor(t, -1)).toBe(t.palette[t.palette.length - 1]);
  });
});
