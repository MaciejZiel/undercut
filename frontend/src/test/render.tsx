import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { AuthProvider } from "@/lib/auth/auth-context";

export function renderWithProviders(ui: ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 0 }, mutations: { retry: false } } });
  return { client, ...render(<QueryClientProvider client={client}><AuthProvider>{ui}</AuthProvider></QueryClientProvider>) };
}

export const USER = {
  id: 7,
  display_name: "Max Fan",
  email: "max@example.com",
  email_verified: true,
  can_predict: true,
  timezone: "Europe/Warsaw",
  theme: "system" as const,
  is_demo: false,
  race_result_email: true,
};

export const ME_ANON = { is_authenticated: false, user: null };
export const ME_USER = { is_authenticated: true, user: USER };
