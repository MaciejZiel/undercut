import { HttpError, isHttpError } from "./http";

/** Rate-limit text shared by every form (login, sign-up, reset, ...). */
export function rateLimitMessage(retryAfter: number | null): string {
  if (retryAfter && retryAfter >= 60) {
    return `Too many attempts. Try again in about ${Math.ceil(retryAfter / 60)} minutes.`;
  }
  return "Too many attempts. Wait a few minutes and try again.";
}

const CODE_MESSAGES: Record<string, string> = {
  email_password_mismatch: "Incorrect e-mail or password.",
  too_many_login_attempts: "Too many failed sign-in attempts. Wait a few minutes and try again.",
  invalid_or_expired_key: "This link is invalid or has expired. Request a new one.",
  email_taken: "This e-mail address is already in use.",
  predictions_locked: "Predictions for this round are closed.",
  email_not_verified: "Verify your e-mail address before making predictions.",
  picks_hidden: "Other players' picks are visible after predictions close.",
  league_full: "This league is full.",
  league_limit_reached: "You have reached the maximum number of leagues.",
  already_member: "You are already a member of this league.",
  not_league_owner: "Only the league owner can do this.",
  owner_cannot_leave: "The owner cannot leave the league. Delete it instead.",
  qualifying_time_unknown: "The lock time of this round is not known yet, so picks are not open.",
  demo_locked: "The demo account cannot be changed.",
};

/** One sentence for the user, for any failure. */
export function describeError(error: unknown, fallback = "Something went wrong. Try again."): string {
  if (!isHttpError(error)) return fallback;
  return describeHttpError(error, fallback);
}

export function describeHttpError(error: HttpError, fallback: string): string {
  if (error.status === 429) return rateLimitMessage(error.retryAfter);
  if (error.status === 0) return error.messages[0] ?? fallback;
  if (error.status >= 500) return "The server had a problem. Try again in a moment.";
  if (error.code && CODE_MESSAGES[error.code]) return CODE_MESSAGES[error.code];
  return error.messages.join(" ") || fallback;
}

/** Field level messages for forms; anything not tied to a field goes to `form`. */
export function formErrors(error: unknown, knownFields: string[]): { form: string | null; fields: Record<string, string> } {
  if (!isHttpError(error)) return { form: describeError(error), fields: {} };
  const fields: Record<string, string> = {};
  let hasField = false;
  if (error.status === 400 || error.status === 409) {
    for (const f of knownFields) {
      const list = error.fields[f];
      if (list?.length) {
        fields[f] = list.join(" ");
        hasField = true;
      }
    }
  }
  if (hasField && Object.keys(error.fields).every((f) => knownFields.includes(f)) && !error.code?.startsWith("too_many")) {
    return { form: null, fields };
  }
  return { form: describeHttpError(error, "Something went wrong. Try again."), fields };
}
