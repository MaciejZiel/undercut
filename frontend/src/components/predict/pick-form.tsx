"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Notice, primaryButton } from "@/components/account/form-parts";
import { useAuth } from "@/lib/auth/auth-context";
import { isHttpError } from "@/lib/auth/http";
import { describeError } from "@/lib/auth/messages";
import { SLOTS, predictKeys, submitPick, type PickableDriver, type RoundState, type RoundStateResult, type SlotKey } from "@/lib/predict/api";
import { Countdown, useRemaining } from "./countdown";
import { DriverCombobox } from "./driver-combobox";

type Draft = Record<SlotKey, number | null>;

function initialDraft(state: RoundState): Draft {
  const p = state.my_pick;
  return {
    p1: p?.p1?.id ?? null,
    p2: p?.p2?.id ?? null,
    p3: p?.p3?.id ?? null,
    pole: p?.pole?.id ?? null,
    fastest_lap: p?.fastest_lap?.id ?? null,
  };
}

/** Ids already taken by the other podium slots, for the "no duplicates on the podium" rule. */
export function podiumTaken(draft: Draft, slot: SlotKey): Set<number> {
  const taken = new Set<number>();
  for (const s of SLOTS) {
    if (s.podium && s.key !== slot && draft[s.key] != null) taken.add(draft[s.key] as number);
  }
  return taken;
}

export function PickForm({
  year,
  round,
  result,
  drivers,
  onExpire,
}: {
  year: number;
  round: number;
  result: RoundStateResult;
  drivers: PickableDriver[];
  onExpire?: () => void;
}) {
  const { state, skewMs } = result;
  const auth = useAuth();
  const client = useQueryClient();
  const [draft, setDraft] = useState<Draft>(() => initialDraft(state));
  const [formError, setFormError] = useState<string | null>(null);
  const [saved, setSaved] = useState<"created" | "updated" | null>(null);
  const remaining = useRemaining(state.closes_at, skewMs);
  const locked = state.status === "closed" || (state.status === "open" && remaining === 0);
  const canPredict = auth.user?.can_predict ?? false;

  const save = useMutation({
    mutationFn: () => submitPick(year, round, draft as Record<SlotKey, number>),
    onSuccess: ({ state: next, created }) => {
      client.setQueryData(predictKeys.round(year, round), { state: next, skewMs });
      void client.invalidateQueries({ queryKey: predictKeys.history });
      setSaved(created ? "created" : "updated");
      setFormError(null);
    },
    onError: (error) => {
      setSaved(null);
      setFormError(describeError(error));
      if (isHttpError(error) && (error.code === "predictions_locked" || error.status === 403)) {
        // The server is the authority on the lock: re-read the state so the form turns read-only.
        void client.invalidateQueries({ queryKey: predictKeys.round(year, round) });
      }
    },
  });

  const missing = SLOTS.filter((s) => draft[s.key] == null);
  const duplicate = new Set([draft.p1, draft.p2, draft.p3].filter((v) => v != null)).size !== [draft.p1, draft.p2, draft.p3].filter((v) => v != null).length;

  if (locked) {
    return (
      <div className="space-y-4">
        <Notice tone="info">Predictions for this round are closed. {state.my_pick ? "Your pick is shown below." : "You did not make a pick."}</Notice>
        <ReadOnlyPick state={state} drivers={drivers} />
      </div>
    );
  }

  return (
    <form
      noValidate
      className="space-y-5"
      onSubmit={(e) => {
        e.preventDefault();
        setSaved(null);
        if (missing.length > 0) {
          setFormError("Choose a driver for every field.");
          return;
        }
        if (duplicate) {
          setFormError("A driver can appear only once on the podium.");
          return;
        }
        setFormError(null);
        save.mutate();
      }}
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2 border-y border-line py-4">
        <span className="text-sm text-muted">Predictions close in</span>
        <Countdown closesAt={state.closes_at} skewMs={skewMs} onExpire={onExpire} />
      </div>
      {state.status === "unavailable" && <Notice tone="info">The qualifying time of this round is not known yet, so picks open once it is published.</Notice>}
      {!canPredict && <Notice tone="info">Confirm your e-mail address to make predictions. Use the link in the banner above to send it again.</Notice>}
      {formError && <Notice>{formError}</Notice>}
      {saved && <Notice tone="success">{saved === "created" ? "Pick saved." : "Pick updated."} You can change it until predictions close.</Notice>}
      <div className="grid gap-4 sm:grid-cols-2">
        {SLOTS.map((slot) => (
          <DriverCombobox
            key={slot.key}
            label={slot.label}
            drivers={drivers}
            value={draft[slot.key]}
            disabledIds={slot.podium ? podiumTaken(draft, slot.key) : undefined}
            disabled={state.status !== "open" || !canPredict}
            onChange={(id) => {
              setSaved(null);
              setDraft((d) => ({ ...d, [slot.key]: id }));
            }}
          />
        ))}
      </div>
      <button type="submit" disabled={save.isPending || state.status !== "open" || !canPredict} className={primaryButton}>
        {save.isPending ? "Saving…" : state.my_pick ? "Update pick" : "Save pick"}
      </button>
    </form>
  );
}

function ReadOnlyPick({ state }: { state: RoundState; drivers: PickableDriver[] }) {
  const pick = state.my_pick;
  if (!pick) return null;
  return (
    <dl className="grid gap-3 border-y border-line py-4 sm:grid-cols-2">
      {SLOTS.map((s) => (
        <div key={s.key}>
          <dt className="text-xs font-bold text-muted">{s.label}</dt>
          <dd className="font-semibold">{pick[s.key]?.name ?? "—"}</dd>
        </div>
      ))}
      {pick.points != null && (
        <div>
          <dt className="text-xs font-bold text-muted">Points</dt>
          <dd className="timing font-semibold">{pick.points}</dd>
        </div>
      )}
    </dl>
  );
}
