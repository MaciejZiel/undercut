import { apiJson, apiRequest } from "./http";

export type GoogleStatus = { enabled: boolean; linked: boolean; email: string | null; has_password: boolean };

export const googleQueryKey = ["google"] as const;

export const fetchGoogleStatus = () => apiJson<GoogleStatus>("/api/v1/auth/google/");

export async function unlinkGoogle(): Promise<void> {
  await apiRequest("/api/v1/auth/google/", { method: "DELETE", accept: [204] });
}

/** Full-page navigation target: the backend answers with a redirect to Google. */
export function googleStartUrl(next?: string | null, mode: "login" | "link" = "login"): string {
  const params = new URLSearchParams();
  if (mode === "link") params.set("mode", "link");
  if (next) params.set("next", next);
  const query = params.toString();
  return `/api/v1/auth/google/start/${query ? `?${query}` : ""}`;
}

const MESSAGES: Record<string, string> = {
  cancelled: "Google sign-in was cancelled.",
  denied: "Google did not allow the sign-in.",
  disabled: "Google sign-in is not available right now.",
  expired: "The Google sign-in took too long. Please try again.",
  invalid_state: "The Google sign-in could not be verified. Please try again.",
  invalid_token: "Google sent an answer we could not trust. Please try again.",
  exchange_failed: "Google could not complete the sign-in. Please try again.",
  unavailable: "Google could not be reached. Please try again in a moment.",
  email_unverified: "Google has not verified this e-mail address, so we cannot use it.",
  email_missing: "Google did not share an e-mail address.",
  email_taken: "An account with this e-mail already exists. Sign in with your password instead.",
  email_unverified_account:
    "An account with this e-mail exists but is not confirmed. Confirm it from the e-mail we sent, or reset the password, then try again.",
  account_unavailable: "This account cannot sign in.",
  already_linked: "This account already has a Google login.",
  google_in_use: "That Google account is already linked to another Undercut account.",
  unauthenticated: "Sign in first, then link your Google account.",
  last_login_method: "Set a password first, so you keep a way to sign in.",
};

export function googleErrorMessage(code: string | null | undefined): string | null {
  if (!code) return null;
  return MESSAGES[code] ?? "Google sign-in failed. Please try again.";
}
