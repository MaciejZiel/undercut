"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import {
  confirmEmail,
  demoLogin,
  inspectResetKey,
  inspectVerificationKey,
  login,
  requestPasswordReset,
  resetPassword,
  signup,
} from "@/lib/auth/api";
import { useAuth } from "@/lib/auth/auth-context";
import { describeError, formErrors } from "@/lib/auth/messages";
import { googleErrorMessage } from "@/lib/auth/google";
import { loginHref, registerHref, safeNext } from "@/lib/auth/redirect";
import { Field, FormCard, Notice, primaryButton, secondaryButton } from "./form-parts";
import { GoogleButton } from "./google-button";

function useNext(): string | null {
  return safeNext(useSearchParams().get("next"));
}

/** Sign-in form. Used on /login and inside the "Sign in to follow" dialog. */
export function LoginForm({
  onSuccess,
  next,
  registerNext,
}: {
  onSuccess?: () => void;
  next?: string | null;
  registerNext?: string | null;
}) {
  const auth = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<{ form: string | null; fields: Record<string, string> }>({ form: null, fields: {} });

  async function finish() {
    await auth.refresh();
    if (onSuccess) onSuccess();
    else router.replace(next ?? "/");
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (busy) return;
    if (!email.trim() || !password) {
      setError({
        form: null,
        fields: {
          ...(email.trim() ? {} : { email: "Enter your e-mail address." }),
          ...(password ? {} : { password: "Enter your password." }),
        },
      });
      return;
    }
    setBusy(true);
    setError({ form: null, fields: {} });
    try {
      await login(email.trim(), password);
      await finish();
    } catch (err) {
      setError(formErrors(err, ["email", "password"]));
    } finally {
      setBusy(false);
    }
  }

  async function tryDemo() {
    setBusy(true);
    setError({ form: null, fields: {} });
    try {
      await demoLogin();
      await finish();
    } catch (err) {
      setError({ form: describeError(err), fields: {} });
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4" noValidate>
      {error.form && <Notice>{error.form}</Notice>}
      <Field
        label="E-mail"
        type="email"
        name="email"
        autoComplete="email"
        required
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        error={error.fields.email}
      />
      <Field
        label="Password"
        type="password"
        name="password"
        autoComplete="current-password"
        required
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        error={error.fields.password}
      />
      <button type="submit" disabled={busy} className={`${primaryButton} w-full`}>
        {busy ? "Signing in…" : "Sign in"}
      </button>
      <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
        <Link href="/reset" className="text-accent underline">
          Forgot your password?
        </Link>
        <Link href={registerHref(registerNext ?? next)} className="text-accent underline">
          Create an account
        </Link>
      </div>
      <button type="button" onClick={tryDemo} disabled={busy} className={`${secondaryButton} w-full`}>
        Try the demo without registering
      </button>
    </form>
  );
}

export function LoginScreen() {
  const next = useNext();
  const auth = useAuth();
  const router = useRouter();
  const googleError = googleErrorMessage(useSearchParams().get("google_error"));
  useEffect(() => {
    if (auth.status === "authenticated") router.replace(next ?? "/");
  }, [auth.status, next, router]);
  return (
    <FormCard title="Sign in">
      {googleError && <Notice className="mb-4">{googleError}</Notice>}
      <div className="space-y-4">
        <LoginForm next={next} />
        <GoogleButton next={next} />
      </div>
    </FormCard>
  );
}

export function RegisterScreen() {
  const next = useNext();
  const auth = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<{ form: string | null; fields: Record<string, string> }>({ form: null, fields: {} });

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setError({ form: null, fields: {} });
    try {
      await signup({ email: email.trim(), password, display_name: displayName.trim() });
      await auth.refresh();
      setDone(true);
    } catch (err) {
      setError(formErrors(err, ["email", "password", "display_name"]));
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <FormCard title="Check your inbox">
        <p className="mb-4">
          We sent a confirmation link to <strong>{email}</strong>. You can already follow drivers; you need a confirmed
          e-mail address to make predictions.
        </p>
        <button type="button" onClick={() => router.replace(next ?? "/")} className={primaryButton}>
          Continue
        </button>
      </FormCard>
    );
  }

  return (
    <FormCard
      title="Create an account"
      footer={
        <>
          Already registered?{" "}
          <Link href={loginHref(next)} className="text-accent underline">
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={submit} className="space-y-4" noValidate>
        {error.form && <Notice>{error.form}</Notice>}
        <Field label="E-mail" type="email" name="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} error={error.fields.email} />
        <Field
          label="Display name"
          name="display_name"
          autoComplete="nickname"
          required
          minLength={3}
          maxLength={20}
          hint="3 to 20 characters. Shown on leaderboards."
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          error={error.fields.display_name}
        />
        <Field
          label="Password"
          type="password"
          name="password"
          autoComplete="new-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={error.fields.password}
        />
        <button type="submit" disabled={busy || !email || !displayName || !password} className={`${primaryButton} w-full`}>
          {busy ? "Creating account…" : "Create account"}
        </button>
      </form>
      <div className="mt-4 space-y-4">
        <GoogleButton next={next} />
      </div>
    </FormCard>
  );
}

type Phase = "checking" | "ready" | "done" | "invalid";

/** Landing page of the confirmation link: validates the key, then confirms on click. */
export function VerifyEmailScreen({ verifyKey }: { verifyKey: string }) {
  const auth = useAuth();
  const [phase, setPhase] = useState<Phase>("checking");
  const [address, setAddress] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    inspectVerificationKey(verifyKey)
      .then((email) => {
        if (cancelled) return;
        setAddress(email);
        setPhase("ready");
      })
      .catch((err) => {
        if (cancelled) return;
        setError(describeError(err, "This link is invalid or has expired."));
        setPhase("invalid");
      });
    return () => {
      cancelled = true;
    };
  }, [verifyKey]);

  async function confirm() {
    setBusy(true);
    setError(null);
    try {
      await confirmEmail(verifyKey);
      await auth.refresh();
      setPhase("done");
    } catch (err) {
      setError(describeError(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <FormCard title="Confirm your e-mail">
      {phase === "checking" && <p role="status">Checking your link…</p>}
      {phase === "ready" && (
        <div className="space-y-4">
          <p>
            Confirm <strong>{address ?? "your e-mail address"}</strong> to unlock predictions.
          </p>
          {error && <Notice>{error}</Notice>}
          <button type="button" onClick={confirm} disabled={busy} className={primaryButton}>
            {busy ? "Confirming…" : "Confirm e-mail"}
          </button>
        </div>
      )}
      {phase === "done" && (
        <div className="space-y-4">
          <Notice tone="success">Your e-mail address is confirmed.</Notice>
          <Link href="/predict" className={primaryButton}>
            Go to predictions
          </Link>
        </div>
      )}
      {phase === "invalid" && (
        <div className="space-y-4">
          <Notice>{error}</Notice>
          <p className="text-sm text-muted">Sign in and use the banner at the top of the page to send a new link.</p>
          <Link href="/login" className={secondaryButton}>
            Sign in
          </Link>
        </div>
      )}
    </FormCard>
  );
}

/** Asks for the e-mail address; the reply is the same whether or not the account exists. */
export function RequestResetScreen() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      await requestPasswordReset(email.trim());
      setSent(true);
    } catch (err) {
      setError(formErrors(err, ["email"]).fields.email ?? describeError(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <FormCard title="Reset your password" footer={<Link href="/login" className="text-accent underline">Back to sign in</Link>}>
      {sent ? (
        <Notice tone="success">If an account exists for {email}, a reset link is on its way. The link works for one hour.</Notice>
      ) : (
        <form onSubmit={submit} className="space-y-4" noValidate>
          {error && <Notice>{error}</Notice>}
          <Field label="E-mail" type="email" name="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          <button type="submit" disabled={busy || !email} className={`${primaryButton} w-full`}>
            {busy ? "Sending…" : "Send reset link"}
          </button>
        </form>
      )}
    </FormCard>
  );
}

export function ResetPasswordScreen({ resetKey }: { resetKey: string }) {
  const router = useRouter();
  const auth = useAuth();
  const [phase, setPhase] = useState<"checking" | "ready" | "invalid" | "done">("checking");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<{ form: string | null; fields: Record<string, string> }>({ form: null, fields: {} });

  useEffect(() => {
    let cancelled = false;
    inspectResetKey(resetKey)
      .then(() => !cancelled && setPhase("ready"))
      .catch((err) => {
        if (cancelled) return;
        setError({ form: describeError(err, "This link is invalid or has expired."), fields: {} });
        setPhase("invalid");
      });
    return () => {
      cancelled = true;
    };
  }, [resetKey]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setError({ form: null, fields: {} });
    try {
      await resetPassword(resetKey, password);
      await auth.refresh();
      setPhase("done");
    } catch (err) {
      setError(formErrors(err, ["password", "key"]));
    } finally {
      setBusy(false);
    }
  }

  return (
    <FormCard title="Choose a new password">
      {phase === "checking" && <p role="status">Checking your link…</p>}
      {phase === "invalid" && (
        <div className="space-y-4">
          <Notice>{error.form}</Notice>
          <Link href="/reset" className={secondaryButton}>
            Request a new link
          </Link>
        </div>
      )}
      {phase === "ready" && (
        <form onSubmit={submit} className="space-y-4" noValidate>
          {error.form && <Notice>{error.form}</Notice>}
          <Field
            label="New password"
            type="password"
            name="password"
            autoComplete="new-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            error={error.fields.password}
          />
          <button type="submit" disabled={busy || !password} className={`${primaryButton} w-full`}>
            {busy ? "Saving…" : "Save password"}
          </button>
        </form>
      )}
      {phase === "done" && (
        <div className="space-y-4">
          <Notice tone="success">Your password was changed.</Notice>
          <button type="button" onClick={() => router.replace("/")} className={primaryButton}>
            Continue
          </button>
        </div>
      )}
    </FormCard>
  );
}
