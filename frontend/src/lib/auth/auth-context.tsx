"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useMemo, type ReactNode } from "react";
import { fetchMe, logout as logoutRequest, queryKeys, type Me, type User } from "./api";

export type AuthStatus = "loading" | "authenticated" | "anonymous" | "error";

type AuthValue = {
  status: AuthStatus;
  user: User | null;
  /** Re-reads /me; call after login, sign-up, demo login and after a 401. */
  refresh: () => Promise<void>;
  /** Replaces the cached user (for example after saving settings). */
  setUser: (user: User) => void;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthValue | null>(null);

/** Query keys that hold per-user data and must never survive a login change. */
const PER_USER_ROOTS = ["favorites", "predict", "leagues"];

export function AuthProvider({ children }: { children: ReactNode }) {
  const client = useQueryClient();
  const query = useQuery({
    queryKey: queryKeys.me,
    queryFn: fetchMe,
    staleTime: 5 * 60_000,
    retry: false,
    refetchOnWindowFocus: true,
  });

  const dropUserData = useCallback(() => {
    for (const root of PER_USER_ROOTS) client.removeQueries({ queryKey: [root] });
  }, [client]);

  const refresh = useCallback(async () => {
    dropUserData();
    await client.invalidateQueries({ queryKey: queryKeys.me });
    await client.refetchQueries({ queryKey: queryKeys.me });
  }, [client, dropUserData]);

  const setUser = useCallback(
    (user: User) => client.setQueryData<Me>(queryKeys.me, { is_authenticated: true, user }),
    [client],
  );

  const logout = useCallback(async () => {
    try {
      await logoutRequest();
    } finally {
      dropUserData();
      client.setQueryData<Me>(queryKeys.me, { is_authenticated: false, user: null });
    }
  }, [client, dropUserData]);

  const value = useMemo<AuthValue>(() => {
    const me = query.data;
    let status: AuthStatus;
    if (me) status = me.is_authenticated && me.user ? "authenticated" : "anonymous";
    else status = query.isError ? "error" : "loading";
    return { status, user: me?.user ?? null, refresh, setUser, logout };
  }, [query.data, query.isError, refresh, setUser, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
