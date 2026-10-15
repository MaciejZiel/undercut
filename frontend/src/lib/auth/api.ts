import type { components } from "@/lib/api/client";
import { apiJson, apiRequest, isHttpError } from "./http";

type Schemas = components["schemas"];
export type User = Schemas["User"];
export type Me = Schemas["Me"];
export type Favorites = Schemas["Favorites"];
export type SettingsUpdate = Schemas["PatchedSettingsUpdate"];

/** django-allauth headless, browser client (session cookie, CSRF header). */
export const ALLAUTH = "/api/v1/allauth/browser/v1";

export const queryKeys = {
  me: ["me"] as const,
  favorites: ["favorites"] as const,
};

export const fetchMe = () => apiJson<Me>("/api/v1/auth/me/");

export async function login(email: string, password: string): Promise<void> {
  await apiRequest(`${ALLAUTH}/auth/login`, { method: "POST", body: { email, password } });
}

export type SignupInput = { email: string; password: string; display_name: string };

export async function signup(input: SignupInput): Promise<void> {
  await apiRequest(`${ALLAUTH}/auth/signup`, { method: "POST", body: input });
}

/** allauth answers 401 (not authenticated) after a successful logout, so 401 is accepted. */
export async function logout(): Promise<void> {
  await apiRequest(`${ALLAUTH}/auth/session`, { method: "DELETE", accept: [401] });
}

export async function demoLogin(): Promise<void> {
  await apiRequest("/api/v1/auth/demo/", { method: "POST" });
}

/** Checks the key from the e-mail link without consuming it. Returns the address being verified. */
export async function inspectVerificationKey(key: string): Promise<string | null> {
  const { data } = await apiRequest<{ data?: { email?: string } }>(`${ALLAUTH}/auth/email/verify`, {
    headers: { "X-Email-Verification-Key": key },
  });
  return data?.data?.email ?? null;
}

/** 200 (logged in) and 401 (confirmed, not logged in) both mean the address is now verified. */
export async function confirmEmail(key: string): Promise<void> {
  await apiRequest(`${ALLAUTH}/auth/email/verify`, { method: "POST", body: { key }, accept: [401] });
}

/** Sends the confirmation mail again for the signed-in user's address. */
export async function resendVerification(email: string): Promise<void> {
  await apiRequest(`${ALLAUTH}/account/email`, { method: "PUT", body: { email } });
}

export async function requestPasswordReset(email: string): Promise<void> {
  await apiRequest(`${ALLAUTH}/auth/password/request`, { method: "POST", body: { email } });
}

export async function inspectResetKey(key: string): Promise<void> {
  await apiRequest(`${ALLAUTH}/auth/password/reset`, { headers: { "X-Password-Reset-Key": key } });
}

export async function resetPassword(key: string, password: string): Promise<void> {
  await apiRequest(`${ALLAUTH}/auth/password/reset`, { method: "POST", body: { key, password }, accept: [401] });
}

export const updateSettings = (patch: SettingsUpdate) =>
  apiJson<User>("/api/v1/account/settings/", { method: "PATCH", body: patch });

export const deleteAccount = (displayName: string) =>
  apiRequest("/api/v1/account/delete/", { method: "POST", body: { display_name: displayName } });

/** Fetches the export and returns the file body as text; saving is the caller's job (blob). */
export async function fetchExport(): Promise<string> {
  const { data } = await apiRequest<unknown>("/api/v1/account/export/");
  return typeof data === "string" ? data : JSON.stringify(data, null, 2);
}

export const fetchFavorites = () => apiJson<Favorites>("/api/v1/favorites/");

export type FavoriteKind = "driver" | "constructor";

export const favoritePath = (kind: FavoriteKind, slug: string) =>
  `/api/v1/favorites/${kind === "driver" ? "drivers" : "constructors"}/${encodeURIComponent(slug)}/`;

export const setFavorite = (kind: FavoriteKind, slug: string, on: boolean) =>
  apiJson<{ favorite: boolean }>(favoritePath(kind, slug), { method: on ? "PUT" : "DELETE" });

export function isUnauthorized(error: unknown): boolean {
  return isHttpError(error) && (error.status === 401 || (error.status === 403 && error.code === "not_authenticated"));
}
