"use client";

import { useId } from "react";
import { SearchIcon } from "@/components/ui/icons";

/** Placeholder: the search results screen (/search) arrives with FR-107. */
export function SearchBox({ className = "" }: { className?: string }) {
  const id = useId();
  return (
    <form role="search" onSubmit={(e) => e.preventDefault()} className={className}>
      <label htmlFor={id} className="sr-only">
        Search drivers, teams and circuits
      </label>
      <div className="relative">
        <SearchIcon className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" />
        <input
          id={id}
          type="search"
          placeholder="Search drivers, teams, circuits"
          autoComplete="off"
          className="t-fast h-10 w-full rounded-md border border-line bg-surface pl-9 pr-3 text-sm placeholder:text-muted hover:border-muted"
        />
      </div>
    </form>
  );
}
