"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { useMemo, useState, type FormEvent } from "react";
import { deleteAccount, fetchExport, updateSettings, type User } from "@/lib/auth/api";
import { useAuth } from "@/lib/auth/auth-context";
import { fetchGoogleStatus, googleErrorMessage, googleQueryKey, googleStartUrl, unlinkGoogle } from "@/lib/auth/google";
import { describeError, formErrors } from "@/lib/auth/messages";
import { applyThemeChoice, browserTimeZone, saveTextFile, timeZoneOptions, type ThemeChoice } from "@/lib/auth/settings";
import { Field, Notice, dangerButton, inputClass, primaryButton, secondaryButton } from "./form-parts";
import { Modal } from "./modal";

export function SettingsScreen() {
  const { user } = useAuth();
  if (!user) return null;
  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
      <ProfileForm user={user} />
      <div className="space-y-8">
        <GoogleSection />
        <ExportSection />
        <DeleteSection user={user} />
      </div>
    </div>
  );
}

function ProfileForm({ user }: { user: User }) {
  const auth = useAuth();
  const [displayName, setDisplayName] = useState(user.display_name ?? "");
  const [timezone, setTimezone] = useState(user.timezone);
  const [theme, setTheme] = useState<ThemeChoice>(user.theme);
  const [emailPref, setEmailPref] = useState(user.race_result_email);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<{ form: string | null; fields: Record<string, string> }>({ form: null, fields: {} });
  const zones = useMemo(() => timeZoneOptions(user.timezone), [user.timezone]);
  const detected = browserTimeZone();
  const locked = user.is_demo;

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setSaved(false);
    setError({ form: null, fields: {} });
    try {
      const updated = await updateSettings({
        display_name: displayName.trim(),
        timezone,
        theme,
        race_result_email: emailPref,
      });
      auth.setUser(updated);
      applyThemeChoice(updated.theme);
      setDisplayName(updated.display_name ?? "");
      setSaved(true);
    } catch (err) {
      setError(formErrors(err, ["display_name", "timezone", "theme", "race_result_email"]));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-5" noValidate aria-labelledby="profile-h">
      <h2 id="profile-h" className="heading text-xl sm:text-[1.375rem]">
        Profile and preferences
      </h2>
      {locked && <Notice tone="info">This is the shared demo account. Its settings cannot be changed.</Notice>}
      {error.form && <Notice>{error.form}</Notice>}
      {saved && <Notice tone="success">Settings saved.</Notice>}
      <Field label="E-mail" value={user.email} readOnly disabled hint={user.email_verified ? "Confirmed" : "Not confirmed yet"} />
      <Field
        label="Display name"
        name="display_name"
        value={displayName}
        minLength={3}
        maxLength={20}
        onChange={(e) => setDisplayName(e.target.value)}
        disabled={locked}
        hint="3 to 20 characters. Shown on leaderboards and in leagues."
        error={error.fields.display_name}
      />
      <div>
        <label htmlFor="tz" className="mb-1 block text-sm font-semibold">
          Time zone
        </label>
        <select id="tz" value={timezone} onChange={(e) => setTimezone(e.target.value)} disabled={locked} className={inputClass}>
          {zones.map((z) => (
            <option key={z} value={z}>
              {z}
            </option>
          ))}
        </select>
        {detected && detected !== timezone && (
          <button type="button" onClick={() => setTimezone(detected)} disabled={locked} className="mt-1 text-sm text-accent underline">
            Use my browser time zone ({detected})
          </button>
        )}
        {error.fields.timezone && <p className="mt-1 text-sm text-danger">{error.fields.timezone}</p>}
      </div>
      <fieldset>
        <legend className="mb-1 text-sm font-semibold">Theme</legend>
        <div className="flex flex-wrap gap-4">
          {(["system", "light", "dark"] as const).map((t) => (
            <label key={t} className="flex items-center gap-2 text-sm capitalize">
              <input type="radio" name="theme" value={t} checked={theme === t} onChange={() => setTheme(t)} disabled={locked} />
              {t}
            </label>
          ))}
        </div>
      </fieldset>
      <fieldset>
        <legend className="mb-1 text-sm font-semibold">E-mail preferences</legend>
        <label className="flex items-start gap-2 text-sm">
          <input type="checkbox" checked={emailPref} onChange={(e) => setEmailPref(e.target.checked)} disabled={locked} className="mt-1" />
          <span>
            Send me a message after each race with my points.
            <span className="block text-xs text-muted">Every message has a one-click unsubscribe link.</span>
          </span>
        </label>
      </fieldset>
      <button type="submit" disabled={busy || locked} className={primaryButton}>
        {busy ? "Saving…" : "Save changes"}
      </button>
    </form>
  );
}

function ExportSection() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function download() {
    setBusy(true);
    setError(null);
    try {
      const text = await fetchExport();
      saveTextFile("undercut-export.json", text);
    } catch (err) {
      setError(describeError(err, "Could not prepare your export."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="export-h" className="border-t border-line pt-6">
      <h2 id="export-h" className="mb-1 heading text-xl sm:text-[1.375rem]">
        Your data
      </h2>
      <p className="mb-3 text-sm text-muted">Download everything we store about you (profile, favourites, predictions) as a JSON file.</p>
      {error && <Notice className="mb-3">{error}</Notice>}
      <button type="button" onClick={download} disabled={busy} className={secondaryButton}>
        {busy ? "Preparing…" : "Download my data"}
      </button>
    </section>
  );
}

function DeleteSection({ user }: { user: User }) {
  const auth = useAuth();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [typed, setTyped] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const name = user.display_name ?? "";
  const matches = name !== "" && typed.trim() === name;

  async function confirm(e: FormEvent) {
    e.preventDefault();
    if (!matches || busy) return;
    setBusy(true);
    setError(null);
    try {
      await deleteAccount(name);
      await auth.logout().catch(() => undefined);
      router.replace("/");
    } catch (err) {
      setError(describeError(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="delete-h" className="rounded-sm border border-danger bg-surface p-5">
      <h2 id="delete-h" className="mb-1 heading text-xl sm:text-[1.375rem] text-danger">
        Delete account
      </h2>
      <p className="mb-3 text-sm text-muted">Permanently removes your profile, favourites and predictions. This cannot be undone.</p>
      <button type="button" onClick={() => setOpen(true)} disabled={user.is_demo} className={dangerButton}>
        Delete my account
      </button>
      <Modal open={open} onClose={() => setOpen(false)} title="Delete your account?">
        <form onSubmit={confirm} className="space-y-4">
          <Notice>This is irreversible. Your predictions and league memberships are deleted for good.</Notice>
          {error && <Notice>{error}</Notice>}
          <Field label={`Type "${name}" to confirm`} value={typed} onChange={(e) => setTyped(e.target.value)} autoComplete="off" />
          <div className="flex flex-wrap gap-2">
            <button type="submit" disabled={!matches || busy} className={dangerButton}>
              {busy ? "Deleting…" : "Delete forever"}
            </button>
            <button type="button" onClick={() => setOpen(false)} className={secondaryButton}>
              Cancel
            </button>
          </div>
        </form>
      </Modal>
    </section>
  );
}

function GoogleSection() {
  const params = useSearchParams();
  const client = useQueryClient();
  const status = useQuery({ queryKey: googleQueryKey, queryFn: fetchGoogleStatus });
  const unlink = useMutation({
    mutationFn: unlinkGoogle,
    onSuccess: () => client.invalidateQueries({ queryKey: googleQueryKey }),
  });
  if (!status.data?.enabled) return null;
  const { linked, email, has_password: hasPassword } = status.data;
  const failure = googleErrorMessage(params.get("google_error")) ?? (unlink.error ? describeError(unlink.error) : null);
  const justLinked = params.get("google") === "linked" && linked;

  return (
    <section aria-labelledby="google-h" className="border-t border-line pt-6">
      <h2 id="google-h" className="mb-1 heading text-xl sm:text-[1.375rem]">
        Google login
      </h2>
      {failure && <Notice className="mb-3">{failure}</Notice>}
      {justLinked && <Notice tone="success" className="mb-3">Google account linked.</Notice>}
      {linked ? (
        <>
          <p className="mb-3 text-sm text-muted">
            Linked to <strong className="text-fg">{email}</strong>. You can sign in with it.
          </p>
          {!hasPassword && (
            <p className="mb-3 text-sm text-muted">
              This account has no password yet. To unlink Google, first set one with “Forgot your password?” on the sign-in page.
            </p>
          )}
          <button type="button" onClick={() => unlink.mutate()} disabled={unlink.isPending || !hasPassword} className={secondaryButton}>
            {unlink.isPending ? "Unlinking…" : "Unlink Google"}
          </button>
        </>
      ) : (
        <>
          <p className="mb-3 text-sm text-muted">Link your Google account to sign in with one click.</p>
          <a href={googleStartUrl("/settings", "link")} className={secondaryButton}>
            Link Google
          </a>
        </>
      )}
    </section>
  );
}
