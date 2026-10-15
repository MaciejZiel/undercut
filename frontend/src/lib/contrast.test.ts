import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const css = readFileSync(join(process.cwd(), "src/app/globals.css"), "utf8");

function tokens(block: string): Record<string, string> {
  const out: Record<string, string> = {};
  let guard = 0;
  for (const m of block.matchAll(/--([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})\s*;/g)) {
    if (++guard > 200) break;
    out[m[1]] = m[2];
  }
  return out;
}

function blockAfter(selector: string): string {
  const start = css.indexOf(selector);
  if (start < 0) throw new Error(`selector not found: ${selector}`);
  const open = css.indexOf("{", start);
  const close = css.indexOf("}", open);
  return css.slice(open + 1, close);
}

const light = tokens(blockAfter("\n:root {"));
const dark = tokens(blockAfter(':root[data-theme="dark"] {'));
const darkMedia = tokens(blockAfter(':root:not([data-theme="light"]) {'));

function channel(v: number): number {
  const c = v / 255;
  return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
}
function luminance(hex: string): number {
  const n = parseInt(hex.slice(1), 16);
  return 0.2126 * channel((n >> 16) & 255) + 0.7152 * channel((n >> 8) & 255) + 0.0722 * channel(n & 255);
}
export function ratio(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

/** [foreground token, background token] pairs that carry text in the UI. */
const TEXT_PAIRS: [string, string][] = [
  ["fg", "bg"],
  ["fg", "surface"],
  ["fg", "surface-2"],
  ["fg-muted", "bg"],
  ["fg-muted", "surface"],
  ["fg-muted", "surface-2"],
  ["accent", "bg"],
  ["accent", "surface"],
  ["accent", "accent-soft"],
  ["accent-fg", "accent"],
  ["danger", "bg"],
  ["danger", "surface"],
  ["bg", "danger"], // danger button label
];
/** Focus ring and similar UI components need 3:1 (WCAG 1.4.11). */
const UI_PAIRS: [string, string][] = [
  ["focus", "bg"],
  ["focus", "surface"],
];

describe("colour tokens", () => {
  it("parses the palettes", () => {
    expect(Object.keys(light).length).toBeGreaterThan(10);
    expect(Object.keys(dark)).toEqual(Object.keys(light));
    expect(darkMedia).toEqual(dark);
  });

  for (const [name, palette] of [["light", light], ["dark", dark]] as const) {
    for (const [fg, bg] of TEXT_PAIRS) {
      it(`${name}: ${fg} on ${bg} meets AA 4.5:1`, () => {
        expect(ratio(palette[fg], palette[bg])).toBeGreaterThanOrEqual(4.5);
      });
    }
    for (const [fg, bg] of UI_PAIRS) {
      it(`${name}: ${fg} on ${bg} meets 3:1`, () => {
        expect(ratio(palette[fg], palette[bg])).toBeGreaterThanOrEqual(3);
      });
    }
  }
});
