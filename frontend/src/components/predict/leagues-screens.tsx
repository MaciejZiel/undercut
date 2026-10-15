"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Field, Notice, dangerButton, inputClass, primaryButton, secondaryButton } from "@/components/account/form-parts";
import { Modal } from "@/components/account/modal";
import { QueryState } from "@/components/account/query-state";
import { RequireAuth } from "@/components/account/require-auth";
import { LoadingSkeleton } from "@/components/states/loading-skeleton";
import { DataTable, Th } from "@/components/ui/data-table";
import { retryServerErrorsOnce } from "@/lib/auth/http";
import { describeError, formErrors } from "@/lib/auth/messages";
import {
  createLeague,
  deleteLeague,
  fetchLeague,
  fetchLeaguePicks,
  fetchLeagues,
  fetchSeasonRounds,
  fetchSeasonYears,
  inviteLink,
  joinLeague,
  leaveLeague,
  parseInviteCode,
  predictKeys,
  removeLeagueMember,
  renewLeagueCode,
  type LeagueDetail,
} from "@/lib/predict/api";
import { LeaderboardPanel } from "./leaderboard";

const leagueHref = (code: string) => `/leagues/${encodeURIComponent(code)}`;

export function LeaguesScreen() {
  return (
    <RequireAuth>
      <LeaguesBody />
    </RequireAuth>
  );
}

function LeaguesBody() {
  const router = useRouter();
  const client = useQueryClient();
  const leagues = useQuery({ queryKey: predictKeys.leagues, queryFn: fetchLeagues, retry: retryServerErrorsOnce });
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [createError, setCreateError] = useState<string | null>(null);
  const [joinError, setJoinError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: (n: string) => createLeague(n),
    onSuccess: (league) => {
      void client.invalidateQueries({ queryKey: predictKeys.leagues });
      router.push(leagueHref(league.invite_code));
    },
    onError: (e) => setCreateError(formErrors(e, ["name"]).fields.name ?? describeError(e)),
  });
  const join = useMutation({
    mutationFn: (c: string) => joinLeague(c),
    onSuccess: (league) => {
      void client.invalidateQueries({ queryKey: predictKeys.leagues });
      router.push(leagueHref(league.invite_code));
    },
    onError: (e) => setJoinError(describeError(e, "Could not join this league.")),
  });

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
      <section aria-labelledby="my-leagues-h">
        <h2 id="my-leagues-h" className="mb-3 text-xl font-extrabold tracking-tight">
          My leagues
        </h2>
        <QueryState
          query={leagues}
          isEmpty={(l) => l.length === 0}
          empty={{ title: "No leagues yet", description: "Create one and invite friends with a link, or join with a code." }}
          skeleton={<LoadingSkeleton variant="cards" rows={2} label="Loading leagues" />}
          errorTitle="Could not load your leagues"
        >
          {(list) => (
            <ul className="grid gap-3 sm:grid-cols-2">
              {list.map((l) => (
                <li key={l.invite_code}>
                  <Link href={leagueHref(l.invite_code)} className="t-fast block rounded-sm border border-line bg-surface p-4 hover:bg-surface-2">
                    <span className="block font-bold">{l.name}</span>
                    <span className="text-sm text-muted">
                      {l.member_count} {l.member_count === 1 ? "member" : "members"}
                      {l.is_owner ? " · you own this league" : ""}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </QueryState>
      </section>
      <div className="space-y-6">
        <form
          noValidate
          className="space-y-3 rounded-sm border border-line bg-surface p-4"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            setCreateError(null);
            if (name.trim()) create.mutate(name.trim());
          }}
        >
          <h2 className="text-lg font-extrabold">Create a league</h2>
          {createError && <Notice>{createError}</Notice>}
          <Field label="League name" maxLength={60} value={name} onChange={(e) => setName(e.target.value)} />
          <button type="submit" disabled={create.isPending || !name.trim()} className={primaryButton}>
            {create.isPending ? "Creating…" : "Create league"}
          </button>
        </form>
        <form
          noValidate
          className="space-y-3 rounded-sm border border-line bg-surface p-4"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            setJoinError(null);
            const c = parseInviteCode(code);
            if (c) join.mutate(c);
          }}
        >
          <h2 className="text-lg font-extrabold">Join a league</h2>
          {joinError && <Notice>{joinError}</Notice>}
          <Field label="Invite code or link" value={code} onChange={(e) => setCode(e.target.value)} autoComplete="off" />
          <button type="submit" disabled={join.isPending || !code.trim()} className={secondaryButton}>
            {join.isPending ? "Joining…" : "Join league"}
          </button>
        </form>
      </div>
    </div>
  );
}

/** /leagues/join/[code]: the invite link. Asks before joining. */
export function JoinLeagueScreen({ code }: { code: string }) {
  return (
    <RequireAuth>
      <JoinBody code={parseInviteCode(code)} />
    </RequireAuth>
  );
}

function JoinBody({ code }: { code: string }) {
  const router = useRouter();
  const client = useQueryClient();
  const [error, setError] = useState<{ message: string; already: boolean } | null>(null);
  const join = useMutation({
    mutationFn: () => joinLeague(code),
    onSuccess: (league) => {
      void client.invalidateQueries({ queryKey: predictKeys.leagues });
      router.replace(leagueHref(league.invite_code));
    },
    onError: (e) => setError({ message: describeError(e, "Could not join this league."), already: (e as { code?: string }).code === "already_member" }),
  });
  return (
    <div className="mx-auto max-w-md space-y-4 rounded-sm border border-line bg-surface p-5">
      <p>
        You were invited to a league with code <strong className="timing">{code}</strong>.
      </p>
      {error && (
        <Notice>
          {error.message}{" "}
          {error.already && (
            <Link href={leagueHref(code)} className="underline">
              Open the league
            </Link>
          )}
        </Notice>
      )}
      <button type="button" onClick={() => join.mutate()} disabled={join.isPending} className={primaryButton}>
        {join.isPending ? "Joining…" : "Join this league"}
      </button>
    </div>
  );
}

export function LeagueScreen({ code }: { code: string }) {
  return (
    <RequireAuth>
      <LeagueBody code={code} />
    </RequireAuth>
  );
}

function LeagueBody({ code }: { code: string }) {
  const query = useQuery({ queryKey: predictKeys.league(code), queryFn: () => fetchLeague(code), retry: retryServerErrorsOnce });
  return (
    <QueryState query={query} errorTitle="Could not load this league" forbidden="League not available">
      {(league) => <LeagueView league={league} />}
    </QueryState>
  );
}

function CopyInvite({ code }: { code: string }) {
  const [status, setStatus] = useState<string | null>(null);
  const link = inviteLink(code, typeof window === "undefined" ? "" : window.location.origin);
  async function copy() {
    try {
      await navigator.clipboard.writeText(link);
      setStatus("Invite link copied.");
    } catch {
      setStatus(`Copy this link: ${link}`);
    }
  }
  return (
    <div className="flex flex-wrap items-center gap-3">
      <code className="timing rounded-sm bg-surface-2 px-2 py-1 text-sm">{code}</code>
      <button type="button" onClick={copy} className={secondaryButton}>
        Copy invite link
      </button>
      <span role="status" className="text-sm text-muted">
        {status}
      </span>
    </div>
  );
}

function LeagueView({ league }: { league: LeagueDetail }) {
  const router = useRouter();
  const client = useQueryClient();
  const code = league.invite_code;
  const [error, setError] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<"delete" | "leave" | "renew" | null>(null);
  const [removing, setRemoving] = useState<number | null>(null);

  const done = () => {
    void client.invalidateQueries({ queryKey: predictKeys.leagues });
    router.replace("/leagues");
  };
  const renew = useMutation({
    mutationFn: () => renewLeagueCode(code),
    onSuccess: (next) => {
      client.removeQueries({ queryKey: predictKeys.league(code) });
      void client.invalidateQueries({ queryKey: predictKeys.leagues });
      router.replace(leagueHref(next.invite_code));
    },
    onError: (e) => setError(describeError(e)),
  });
  const del = useMutation({ mutationFn: () => deleteLeague(code), onSuccess: done, onError: (e) => setError(describeError(e)) });
  const leave = useMutation({ mutationFn: () => leaveLeague(code), onSuccess: done, onError: (e) => setError(describeError(e)) });
  const remove = useMutation({
    mutationFn: (userId: number) => removeLeagueMember(code, userId),
    onSuccess: () => {
      setRemoving(null);
      void client.invalidateQueries({ queryKey: predictKeys.league(code) });
    },
    onError: (e) => setError(describeError(e)),
  });

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-extrabold tracking-tight">{league.name}</h2>
        <p className="mt-1 text-sm text-muted">
          {league.member_count} of {league.max_members} members
        </p>
        <div className="mt-3">
          <CopyInvite code={code} />
        </div>
        {error && <Notice className="mt-3">{error}</Notice>}
        <div className="mt-3 flex flex-wrap gap-2">
          {league.is_owner ? (
            <>
              <button type="button" onClick={() => setConfirm("renew")} className={secondaryButton}>
                Renew invite code
              </button>
              <button type="button" onClick={() => setConfirm("delete")} className={dangerButton}>
                Delete league
              </button>
            </>
          ) : (
            <button type="button" onClick={() => setConfirm("leave")} className={secondaryButton}>
              Leave league
            </button>
          )}
        </div>
      </div>

      <section aria-labelledby="lg-board-h">
        <h3 id="lg-board-h" className="mb-3 text-xl font-extrabold tracking-tight">
          Leaderboard
        </h3>
        <LeaderboardPanel league={code} />
      </section>

      <section aria-labelledby="lg-members-h">
        <h3 id="lg-members-h" className="mb-3 text-xl font-extrabold tracking-tight">
          Members
        </h3>
        <ul className="divide-y divide-line rounded-sm border border-line bg-surface">
          {league.members.map((m) => (
            <li key={m.user_id} className="flex items-center justify-between gap-3 px-4 py-2.5">
              <span>
                {m.name}
                {m.user_id === league.owner_id && <span className="ml-2 text-xs text-muted">owner</span>}
              </span>
              {league.is_owner && m.user_id !== league.owner_id &&
                (removing === m.user_id ? (
                  <span className="flex items-center gap-2 text-sm">
                    Remove {m.name}?
                    <button type="button" className={dangerButton} onClick={() => remove.mutate(m.user_id)} disabled={remove.isPending}>
                      Remove
                    </button>
                    <button type="button" className={secondaryButton} onClick={() => setRemoving(null)}>
                      Cancel
                    </button>
                  </span>
                ) : (
                  <button type="button" onClick={() => setRemoving(m.user_id)} aria-label={`Remove ${m.name} from the league`} className="text-sm text-danger underline">
                    Remove
                  </button>
                ))}
            </li>
          ))}
        </ul>
      </section>

      <LeaguePicks code={code} />

      <Modal open={confirm !== null} onClose={() => setConfirm(null)} title={confirm === "delete" ? "Delete this league?" : confirm === "leave" ? "Leave this league?" : "Renew the invite code?"}>
        <p className="mb-4 text-sm text-muted">
          {confirm === "delete" && "The league and its leaderboard are removed for every member. This cannot be undone."}
          {confirm === "leave" && "You will stop appearing on this league's leaderboard. You can rejoin with the invite link."}
          {confirm === "renew" && "The current code and link stop working. Share the new one with anybody you still want to invite."}
        </p>
        <div className="flex gap-2">
          <button
            type="button"
            className={confirm === "delete" ? dangerButton : primaryButton}
            onClick={() => {
              const action = confirm;
              setConfirm(null);
              setError(null);
              if (action === "delete") del.mutate();
              else if (action === "leave") leave.mutate();
              else if (action === "renew") renew.mutate();
            }}
          >
            {confirm === "delete" ? "Delete league" : confirm === "leave" ? "Leave league" : "Renew code"}
          </button>
          <button type="button" className={secondaryButton} onClick={() => setConfirm(null)}>
            Cancel
          </button>
        </div>
      </Modal>
    </div>
  );
}

/** Everybody's picks for one round. The API answers 403 until predictions for that round close. */
function LeaguePicks({ code }: { code: string }) {
  const years = useQuery({ queryKey: predictKeys.seasons, queryFn: fetchSeasonYears, staleTime: 10 * 60_000 });
  const year = years.data?.[0];
  const rounds = useQuery({
    queryKey: predictKeys.season(year ?? 0),
    queryFn: () => fetchSeasonRounds(year as number),
    enabled: year !== undefined,
    staleTime: 10 * 60_000,
  });
  const [chosen, setRound] = useState<number | null>(null);
  // Default to the last round that already has a winner, else the first one.
  const valid = rounds.data?.filter((r) => r.round != null && !r.is_cancelled) ?? [];
  const finished = valid.filter((r) => r.winner != null);
  const round = chosen ?? (finished[finished.length - 1] ?? valid[0])?.round ?? null;
  const picks = useQuery({
    queryKey: predictKeys.leaguePicks(code, year ?? 0, round ?? 0),
    queryFn: () => fetchLeaguePicks(code, year as number, round as number),
    enabled: year !== undefined && round !== null,
    retry: retryServerErrorsOnce,
  });
  return (
    <section aria-labelledby="lg-picks-h">
      <h3 id="lg-picks-h" className="mb-3 text-xl font-extrabold tracking-tight">
        Picks by round
      </h3>
      <div className="mb-3">
        <label htmlFor="lg-round" className="mb-1 block text-sm font-semibold">
          Round
        </label>
        <select
          id="lg-round"
          className={inputClass}
          value={round ?? ""}
          onChange={(e) => setRound(e.target.value ? Number(e.target.value) : null)}
        >
          {rounds.data
            ?.filter((r) => r.round != null && !r.is_cancelled)
            .map((r) => (
              <option key={r.round} value={r.round as number}>
                {year} · {r.round}. {r.name}
              </option>
            ))}
        </select>
      </div>
      {round === null ? (
        <p className="text-sm text-muted">Choose a round to see everybody&apos;s picks.</p>
      ) : (
        <QueryState
          query={picks}
          isEmpty={(p) => p.length === 0}
          empty={{ title: "No picks for this round", description: "Nobody in this league made a pick." }}
          forbidden="Picks are hidden for now"
          errorTitle="Could not load the picks"
        >
          {(list) => (
            <DataTable caption="League picks" minWidth="40rem">
              <thead>
                <tr>
                  <Th>Player</Th>
                  <Th>P1</Th>
                  <Th>P2</Th>
                  <Th>P3</Th>
                  <Th>Pole</Th>
                  <Th>Fastest lap</Th>
                  <Th align="right">Points</Th>
                </tr>
              </thead>
              <tbody>
                {list.map((m) => (
                  <tr key={`${m.user_id ?? m.name}`} className="border-b border-line last:border-b-0">
                    <td className="px-3 py-2.5 font-semibold">{m.name}</td>
                    {[m.pick.p1, m.pick.p2, m.pick.p3, m.pick.pole, m.pick.fastest_lap].map((d, i) => (
                      <td key={i} className="timing px-3 py-2.5">
                        {d ? (d.code ?? d.name) : "—"}
                      </td>
                    ))}
                    <td className="timing px-3 py-2.5 text-right font-bold">{m.points ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </DataTable>
          )}
        </QueryState>
      )}
    </section>
  );
}
