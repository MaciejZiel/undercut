"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchGoogleStatus, googleQueryKey, googleStartUrl } from "@/lib/auth/google";
import { secondaryButton } from "./form-parts";

function GoogleMark() {
  return (
    <svg aria-hidden="true" viewBox="0 0 48 48" className="mr-2 h-4 w-4">
      <path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9.1 3.6l6.8-6.8C35.8 2.4 30.3 0 24 0 14.6 0 6.5 5.4 2.6 13.2l7.9 6.1C12.4 13.6 17.7 9.5 24 9.5z" />
      <path fill="#4285F4" d="M46.5 24.5c0-1.6-.1-3.1-.4-4.5H24v9h12.7c-.6 3-2.3 5.5-4.8 7.2l7.5 5.8c4.4-4.1 7.1-10.1 7.1-17.5z" />
      <path fill="#FBBC05" d="M10.5 28.7a14.5 14.5 0 0 1 0-9.4l-7.9-6.1a24 24 0 0 0 0 21.6l7.9-6.1z" />
      <path fill="#34A853" d="M24 48c6.5 0 11.9-2.1 15.9-5.8l-7.5-5.8c-2.1 1.4-4.9 2.3-8.4 2.3-6.3 0-11.6-4.1-13.5-9.8l-7.9 6.1C6.5 42.6 14.6 48 24 48z" />
    </svg>
  );
}

/** "Continue with Google". Renders nothing when the backend has no Google keys configured. */
export function GoogleButton({ next }: { next?: string | null }) {
  const status = useQuery({ queryKey: googleQueryKey, queryFn: fetchGoogleStatus, staleTime: 5 * 60_000 });
  // Keep the room while the answer is on its way, so the page below does not jump.
  if (status.isPending) return <div aria-hidden="true" className="h-[6.5rem]" />;
  if (!status.data?.enabled) return null;
  return (
    <>
      <div className="flex items-center gap-3 text-sm text-muted" role="separator">
        <span className="h-px flex-1 bg-line" />
        or
        <span className="h-px flex-1 bg-line" />
      </div>
      {/* A plain link: the browser must follow the redirect to Google. */}
      <a href={googleStartUrl(next)} className={`${secondaryButton} w-full`}>
        <GoogleMark />
        Continue with Google
      </a>
    </>
  );
}
