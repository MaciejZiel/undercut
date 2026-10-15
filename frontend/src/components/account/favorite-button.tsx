"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { fetchFavorites, queryKeys, setFavorite, type FavoriteKind, type Favorites } from "@/lib/auth/api";
import { useAuth } from "@/lib/auth/auth-context";
import { isHttpError } from "@/lib/auth/http";
import { describeError } from "@/lib/auth/messages";
import { SignInDialog } from "./sign-in-dialog";

const LIST_KEY = { driver: "drivers", constructor: "constructors" } as const;

export function limitMessage(kind: FavoriteKind, limit: number): string {
  return `You can follow up to ${limit} ${LIST_KEY[kind]}. Unfollow one to add another.`;
}

function StarIcon({ filled }: { filled: boolean }) {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" fill={filled ? "currentColor" : "none"}>
      <path d="m12 3 2.7 5.6 6.1.8-4.5 4.3 1.1 6.1L12 16.8 6.6 19.8l1.1-6.1L3.2 9.4l6.1-.8L12 3Z" />
    </svg>
  );
}

function applyChange(data: Favorites, kind: FavoriteKind, slug: string, name: string, on: boolean): Favorites {
  if (kind === "driver") {
    const rest = data.drivers.filter((d) => d.slug !== slug);
    return { ...data, drivers: on ? [...rest, { slug, name, code: null }] : rest };
  }
  const rest = data.constructors.filter((c) => c.slug !== slug);
  return { ...data, constructors: on ? [...rest, { slug, name }] : rest };
}

/**
 * Star toggle for a driver or constructor. Optimistic with rollback; a logged-out click opens a
 * "Sign in to follow" dialog and performs the follow right after the login succeeds.
 */
export function FavoriteButton({ kind, slug, name, className = "" }: { kind: FavoriteKind; slug: string; name: string; className?: string }) {
  const auth = useAuth();
  const client = useQueryClient();
  const [dialog, setDialog] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const signedIn = auth.status === "authenticated";

  const favorites = useQuery({ queryKey: queryKeys.favorites, queryFn: fetchFavorites, enabled: signedIn });
  const list = favorites.data?.[LIST_KEY[kind]];
  const active = !!list?.some((f) => f.slug === slug);
  const limit = favorites.data?.limits[LIST_KEY[kind]];

  const toggle = useMutation({
    mutationFn: (on: boolean) => setFavorite(kind, slug, on),
    onMutate: async (on) => {
      setMessage(null);
      await client.cancelQueries({ queryKey: queryKeys.favorites });
      const previous = client.getQueryData<Favorites>(queryKeys.favorites);
      if (previous) client.setQueryData(queryKeys.favorites, applyChange(previous, kind, slug, name, on));
      return { previous };
    },
    onError: (error, on, ctx) => {
      if (ctx?.previous) client.setQueryData(queryKeys.favorites, ctx.previous);
      if (isHttpError(error) && error.code === "favorite_limit") setMessage(limitMessage(kind, limit ?? 0));
      else if (isHttpError(error) && error.status === 409) setMessage(limitMessage(kind, limit ?? (kind === "driver" ? 10 : 5)));
      else setMessage(describeError(error, `Could not ${on ? "follow" : "unfollow"} ${name}.`));
    },
    onSettled: () => client.invalidateQueries({ queryKey: queryKeys.favorites }),
  });

  function onClick() {
    if (!signedIn) {
      setDialog(true);
      return;
    }
    const next = !active;
    if (next && list && limit !== undefined && list.length >= limit) {
      setMessage(limitMessage(kind, limit));
      return;
    }
    toggle.mutate(next);
  }

  async function afterSignIn() {
    setDialog(false);
    try {
      await setFavorite(kind, slug, true);
      setMessage(null);
    } catch (error) {
      setMessage(isHttpError(error) && error.status === 409 ? limitMessage(kind, kind === "driver" ? 10 : 5) : describeError(error));
    } finally {
      await client.invalidateQueries({ queryKey: queryKeys.favorites });
    }
  }

  return (
    <div className={`flex flex-wrap items-center gap-3 ${className}`}>
      <button
        type="button"
        onClick={onClick}
        aria-pressed={signedIn ? active : false}
        aria-label={active ? `Unfollow ${name}` : `Follow ${name}`}
        disabled={auth.status === "loading" || (signedIn && favorites.isPending)}
        className={`t-fast inline-flex items-center gap-2 rounded-sm border px-3.5 py-2 text-sm font-semibold active:translate-y-px disabled:opacity-60 ${active ? "border-flag bg-flag text-on-flag" : "border-fg bg-transparent text-fg hover:bg-fg hover:text-bg"}`}
      >
        <StarIcon filled={active} />
        <span>{active ? "Following" : "Follow"}</span>
      </button>
      <span role="status" className="text-sm text-danger">
        {message}
      </span>
      <SignInDialog open={dialog} onClose={() => setDialog(false)} onSignedIn={afterSignIn} />
    </div>
  );
}
