import path from "node:path";

export const BASE_URL = process.env.E2E_BASE_URL ?? "http://localhost:8080";

/** The Docker Compose project lives in the repository root (the folder above e2e/). */
export const REPO_ROOT = process.env.E2E_REPO_ROOT ?? path.resolve(__dirname, "..", "..");

/**
 * The API throttles anonymous clients at 60 requests a minute per address, and the test browser
 * is one address that loads many pages. The Next.js server is exempt through the shared token,
 * so the tests send it too. Without the variable nothing is added (and nothing is exempt).
 */
const token = process.env.E2E_INTERNAL_TOKEN ?? "";

const extraHTTPHeaders: Record<string, string> = token ? { "X-Internal-Token": token } : {};

export const contextOptions = { extraHTTPHeaders };

/** A password the validators accept and that shares nothing with the generated e-mail or name. */
export const PASSWORD = "Podium-Gap-7731!";
