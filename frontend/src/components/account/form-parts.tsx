"use client";

import { useId, type InputHTMLAttributes, type ReactNode } from "react";

export const primaryButton =
  "t-fast inline-flex items-center justify-center rounded-sm bg-accent px-4 py-2.5 text-sm font-bold text-accent-fg hover:opacity-85 active:translate-y-px disabled:cursor-not-allowed disabled:opacity-50";
export const secondaryButton =
  "t-fast inline-flex items-center justify-center rounded-sm border border-fg bg-transparent px-4 py-2.5 text-sm font-semibold hover:bg-fg hover:text-bg active:translate-y-px disabled:cursor-not-allowed disabled:opacity-50";
export const dangerButton =
  "t-fast inline-flex items-center justify-center rounded-sm bg-danger px-4 py-2.5 text-sm font-bold text-bg hover:opacity-85 active:translate-y-px disabled:cursor-not-allowed disabled:opacity-50";
export const inputClass =
  "w-full rounded-sm border border-line bg-surface px-3 py-2.5 text-sm text-fg placeholder:text-muted focus-visible:border-fg disabled:opacity-60";

export function Field({
  label,
  error,
  hint,
  ...input
}: { label: string; error?: string; hint?: string } & InputHTMLAttributes<HTMLInputElement>) {
  const id = useId();
  const errId = `${id}-err`;
  const hintId = `${id}-hint`;
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-sm font-semibold">
        {label}
      </label>
      <input
        id={id}
        {...input}
        aria-invalid={error ? true : undefined}
        aria-describedby={[error ? errId : null, hint ? hintId : null].filter(Boolean).join(" ") || undefined}
        className={`${inputClass} ${error ? "border-danger" : ""}`}
      />
      {hint && (
        <p id={hintId} className="mt-1 text-xs text-muted">
          {hint}
        </p>
      )}
      {error && (
        <p id={errId} className="mt-1 text-sm text-danger">
          {error}
        </p>
      )}
    </div>
  );
}

/** Inline message region. Errors use role=alert, success and info use role=status. */
export function Notice({
  tone = "error",
  children,
  className = "",
}: {
  tone?: "error" | "success" | "info";
  children: ReactNode;
  className?: string;
}) {
  const color =
    tone === "error" ? "border-danger text-danger" : tone === "success" ? "border-line text-fg" : "border-line text-muted";
  return (
    <div role={tone === "error" ? "alert" : "status"} className={`rounded-sm border bg-surface px-3 py-2 text-sm ${color} ${className}`}>
      {children}
    </div>
  );
}

export function FormCard({ title, children, footer }: { title: string; children: ReactNode; footer?: ReactNode }) {
  return (
    <div className="mx-auto w-full max-w-md">
      <h1 className="mb-6 text-3xl font-extrabold tracking-tight">{title}</h1>
      <div className="rounded-sm border border-line bg-surface p-5">{children}</div>
      {footer && <div className="mt-4 text-sm text-muted">{footer}</div>}
    </div>
  );
}
