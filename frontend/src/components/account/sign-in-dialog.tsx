"use client";

import { Modal } from "./modal";
import { LoginForm } from "./auth-forms";

/** Modal sign-in used when a logged-out visitor clicks something that needs an account. */
export function SignInDialog({
  open,
  onClose,
  onSignedIn,
  title = "Sign in to follow",
  description = "Sign in to keep your favourites and get them on your dashboard.",
}: {
  open: boolean;
  onClose: () => void;
  /** Runs after the session exists, so the pending action can be performed. */
  onSignedIn: () => void | Promise<void>;
  title?: string;
  description?: string;
}) {
  return (
    <Modal open={open} onClose={onClose} title={title}>
      <p className="mb-4 text-sm text-muted">{description}</p>
      <LoginForm
        registerNext={typeof window === "undefined" ? null : window.location.pathname}
        onSuccess={() => void onSignedIn()}
      />
    </Modal>
  );
}
