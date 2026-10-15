import { THEME_STORAGE_KEY } from "@/lib/theme";

export type ThemeChoice = "system" | "light" | "dark";

/** IANA zones the browser knows, with the current value and UTC always present. */
export function timeZoneOptions(current?: string): string[] {
  let zones: string[] = [];
  try {
    const intl = Intl as unknown as { supportedValuesOf?: (key: string) => string[] };
    zones = intl.supportedValuesOf?.("timeZone") ?? [];
  } catch {
    zones = [];
  }
  const set = new Set(zones);
  set.add("UTC");
  if (current) set.add(current);
  return [...set].sort((a, b) => a.localeCompare(b));
}

export function browserTimeZone(): string | null {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || null;
  } catch {
    return null;
  }
}

/** Applies the saved theme to the page: light/dark are stored, "system" clears the override. */
export function applyThemeChoice(choice: ThemeChoice): void {
  const root = document.documentElement;
  try {
    if (choice === "system") {
      root.removeAttribute("data-theme");
      window.localStorage.removeItem(THEME_STORAGE_KEY);
    } else {
      root.setAttribute("data-theme", choice);
      window.localStorage.setItem(THEME_STORAGE_KEY, choice);
    }
  } catch {
    // Storage can be blocked; the attribute still applies for this page.
  }
}

/** Saves text as a file through a Blob and an object URL (never a data: URL). */
export function saveTextFile(filename: string, text: string, type = "application/json"): void {
  const url = URL.createObjectURL(new Blob([text], { type }));
  try {
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.rel = "noopener";
    document.body.appendChild(a);
    a.click();
    a.remove();
  } finally {
    setTimeout(() => URL.revokeObjectURL(url), 0);
  }
}
