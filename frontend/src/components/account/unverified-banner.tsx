"use client";

import { useState } from "react";
import { resendVerification } from "@/lib/auth/api";
import { useAuth } from "@/lib/auth/auth-context";
import { describeError } from "@/lib/auth/messages";

/** Slim bar under the header for signed-in users whose e-mail address is not confirmed yet. */
export function UnverifiedBanner() {
  const { user } = useAuth();
  const [state, setState] = useState<"idle" | "sending" | "sent">("idle");
  const [error, setError] = useState<string | null>(null);
  if (!user || user.email_verified || user.is_demo) return null;

  async function resend() {
    if (!user) return;
    setState("sending");
    setError(null);
    try {
      await resendVerification(user.email);
      setState("sent");
    } catch (err) {
      setError(describeError(err));
      setState("idle");
    }
  }

  return (
    <div className="border-t border-line bg-accent-soft text-sm" data-testid="unverified-banner">
      <div className="mx-auto flex w-full max-w-7xl flex-wrap items-center gap-x-4 gap-y-1 px-4 py-2">
        <p className="text-fg">
          Confirm your e-mail address ({user.email}) to make predictions.
        </p>
        <button
          type="button"
          onClick={resend}
          disabled={state !== "idle"}
          className="t-fast font-bold text-accent underline disabled:no-underline disabled:opacity-70"
        >
          {state === "sent" ? "Link sent" : state === "sending" ? "Sending…" : "Resend link"}
        </button>
        <span role={error ? "alert" : "status"} className="text-danger">
          {error}
        </span>
      </div>
    </div>
  );
}
