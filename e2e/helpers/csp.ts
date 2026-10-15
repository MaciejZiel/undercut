import type { Page } from "@playwright/test";

/** Collects Content-Security-Policy violations the browser reports in its console. */
export function trackCspViolations(page: Page): string[] {
  const violations: string[] = [];
  page.on("console", (message) => {
    const text = message.text();
    if (/Content Security Policy|Refused to (load|execute|frame|connect|apply)/i.test(text)) {
      violations.push(text);
    }
  });
  return violations;
}
