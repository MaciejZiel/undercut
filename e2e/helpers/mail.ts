import { compose } from "./compose";

/**
 * The backend runs with DJANGO_DEBUG=true, so e-mail goes to the container log. A message is
 * printed as headers plus a body that may be quoted-printable (soft line breaks `=` + newline,
 * `=3D` for `=`) or base64.
 */
const SEPARATOR = /^-{20,}\s*$/m;

export function decodeQuotedPrintable(text: string): string {
  return text
    .replace(/=\r?\n/g, "")
    .replace(/=([0-9A-Fa-f]{2})/g, (_, hex: string) => String.fromCharCode(parseInt(hex, 16)));
}

function decodeMessage(raw: string): string {
  const [head = "", ...rest] = raw.split(/\r?\n\r?\n/);
  const body = rest.join("\n\n");
  if (/content-transfer-encoding:\s*base64/i.test(head)) {
    return `${head}\n\n${Buffer.from(body.replace(/\s+/g, ""), "base64").toString("utf8")}`;
  }
  return decodeQuotedPrintable(raw);
}

/**
 * Path of the newest confirmation link sent to `email` (for example
 * `/account/verify-email/MQ%3A1tQ...`), or null when no such message is in the log text.
 */
export function findVerificationPath(log: string, email: string): string | null {
  const wanted = email.toLowerCase();
  let found: string | null = null;
  for (const message of log.split(SEPARATOR)) {
    const decoded = decodeMessage(message);
    const addressed = decoded
      .split(/\r?\n/)
      .some((line) => /^to:/i.test(line) && line.toLowerCase().includes(wanted));
    if (!addressed) continue;
    const links = [...decoded.matchAll(/\/account\/verify-email\/([^\s"'<>)]+)/g)];
    const last = links.at(-1);
    if (last?.[1]) found = `/account/verify-email/${last[1].replace(/[.,;]+$/, "")}`;
  }
  return found;
}

/** Polls the backend log until the confirmation mail for `email` shows up. */
export async function waitForVerificationPath(email: string, timeoutMs = 45_000): Promise<string> {
  const deadline = Date.now() + timeoutMs;
  for (;;) {
    const log = await compose(["logs", "--no-log-prefix", "--since", "15m", "backend"]);
    const path = findVerificationPath(log, email);
    if (path) return path;
    if (Date.now() > deadline) throw new Error(`No confirmation e-mail for ${email} in the backend log`);
    await new Promise((resolve) => setTimeout(resolve, 1_000));
  }
}

/** The key inside a link path, URL-decoded (the colons arrive as %3A). */
export function keyFromPath(linkPath: string): string {
  return decodeURIComponent(linkPath.replace("/account/verify-email/", ""));
}
