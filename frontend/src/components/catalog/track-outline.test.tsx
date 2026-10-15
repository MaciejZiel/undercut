import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TrackOutline } from "./track-outline";

const points = [
  [0, 0],
  [500, 0],
  [500, 300],
  [0, 300],
  [0, 0],
];

describe("TrackOutline", () => {
  it("draws the line and marks the start when the start is known", () => {
    const { container } = render(<TrackOutline outline={{ width: 500, height: 300, points }} name="Test Circuit" />);
    expect(container.querySelector('svg[aria-label="Outline of Test Circuit"]')).not.toBeNull();
    expect(container.querySelector("rect")).not.toBeNull();
  });

  it("draws no start mark when the outline does not know where the line is", () => {
    const { container } = render(<TrackOutline outline={{ width: 500, height: 300, points, marker: false }} name="Test Circuit" />);
    expect(container.querySelector("path")).not.toBeNull();
    expect(container.querySelector("rect")).toBeNull();
  });

  it("draws nothing for a line with fewer than three points", () => {
    const { container } = render(<TrackOutline outline={{ width: 1, height: 1, points: [[0, 0]] }} name="X" />);
    expect(container.querySelector("svg")).toBeNull();
  });

  it("uses a bare line, with no casing and no start mark, as a small mark", () => {
    const { container } = render(<TrackOutline outline={{ width: 500, height: 300, points }} name="X" variant="mark" />);
    expect(container.querySelectorAll("path")).toHaveLength(1);
    expect(container.querySelector("rect")).toBeNull();
  });
});
