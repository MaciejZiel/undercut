import { fireEvent, render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DetailsDismiss } from "./details-dismiss";

function menu() {
  const { container } = render(
    <div>
      <details open>
        <DetailsDismiss />
        <summary>Menu</summary>
        <a href="/x">Item</a>
      </details>
      <button type="button">Elsewhere</button>
    </div>,
  );
  return container.querySelector("details") as HTMLDetailsElement;
}

describe("DetailsDismiss", () => {
  it("closes the menu on Escape", () => {
    const details = menu();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(details.open).toBe(false);
  });
  it("closes it on a click outside but not inside", () => {
    const details = menu();
    fireEvent.pointerDown(details.querySelector("a") as Element);
    expect(details.open).toBe(true);
    fireEvent.pointerDown(document.querySelector("button") as Element);
    expect(details.open).toBe(false);
  });
});
