"use client";

import { applyTheme, currentTheme } from "@/lib/theme";
import { MoonIcon, SunIcon } from "@/components/ui/icons";

export function ThemeToggle() {
  // Both icons are rendered; CSS shows the one matching the active theme, so
  // there is no server/client mismatch and no flash.
  return (
    <button
      type="button"
      onClick={() => applyTheme(currentTheme() === "dark" ? "light" : "dark")}
      aria-label="Switch between light and dark theme"
      title="Switch theme"
      className="t-fast grid size-11 place-items-center rounded-md text-fg hover:bg-surface hover:text-accent"
    >
      <MoonIcon className="show-in-light" />
      <SunIcon className="show-in-dark" />
    </button>
  );
}
