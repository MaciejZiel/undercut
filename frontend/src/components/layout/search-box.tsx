"use client";

import { useRouter } from "next/navigation";
import { useEffect, useId, useMemo, useRef, useState, type KeyboardEvent as ReactKeyboardEvent } from "react";
import { SearchIcon } from "@/components/ui/icons";
import { createApiClient } from "@/lib/api/client";
import { MIN_QUERY_LENGTH, groupSuggestions, searchHref, type SuggestionGroup } from "@/lib/search";

const DEBOUNCE_MS = 200;

type Status = "idle" | "loading" | "ready" | "error";

/**
 * Header search with grouped suggestions (ARIA combobox with a listbox).
 * Keys: "/" focuses it from anywhere, arrows move, Enter opens the highlighted
 * suggestion or the full results page, Escape closes.
 */
export function SearchBox({ className = "" }: { className?: string }) {
  const id = useId();
  const listId = `${id}-list`;
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [value, setValue] = useState("");
  const [groups, setGroups] = useState<SuggestionGroup[]>([]);
  const [status, setStatus] = useState<Status>("idle");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);

  const flat = useMemo(() => groups.flatMap((g) => g.items), [groups]);
  const query = value.trim();
  const searchable = query.length >= MIN_QUERY_LENGTH;

  // Debounced lookup; the previous request is aborted when the text changes.
  useEffect(() => {
    if (!searchable) return;
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      setStatus("loading");
      try {
        const { data, response } = await createApiClient(window.location.origin).GET("/api/v1/search/", {
          params: { query: { q: query } },
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        if (!response.ok || !data) throw new Error(String(response.status));
        setGroups(groupSuggestions(data));
        setActive(-1);
        setStatus("ready");
      } catch {
        if (controller.signal.aborted) return;
        setGroups([]);
        setStatus("error");
      }
    }, DEBOUNCE_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query, searchable]);

  // "/" focuses the visible search box (the header renders one per breakpoint).
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key !== "/" || e.ctrlKey || e.metaKey || e.altKey || e.defaultPrevented) return;
      const t = e.target as HTMLElement | null;
      if (t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName))) return;
      const input = inputRef.current;
      if (!input || input.getClientRects().length === 0) return; // hidden at this breakpoint
      e.preventDefault();
      input.focus();
      input.select();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  function go(href: string) {
    setOpen(false);
    setActive(-1);
    router.push(href);
  }

  function onKeyDown(e: ReactKeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      if (flat.length === 0) return;
      e.preventDefault();
      setOpen(true);
      const step = e.key === "ArrowDown" ? 1 : -1;
      setActive((a) => (a + step + flat.length + (a === -1 && step === -1 ? 1 : 0)) % flat.length);
    } else if (e.key === "Escape") {
      if (open) {
        e.preventDefault();
        setOpen(false);
        setActive(-1);
      }
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (open && active >= 0 && flat[active]) go(flat[active].href);
      else if (searchable) go(searchHref(query));
    }
  }

  const showPanel = open && searchable && status !== "idle";
  const activeId = active >= 0 && flat[active] ? `${id}-opt-${flat[active].id}` : undefined;
  // Flat index of the first item of each group, for aria-selected.
  const offsets = groups.map((_, i) => groups.slice(0, i).reduce((n, g) => n + g.items.length, 0));

  return (
    <form
      role="search"
      onSubmit={(e) => e.preventDefault()}
      className={className}
      onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget)) setOpen(false);
      }}
    >
      <label htmlFor={id} className="sr-only">
        Search drivers, teams, circuits and races
      </label>
      <div className="relative">
        <SearchIcon className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" />
        <input
          ref={inputRef}
          id={id}
          type="search"
          role="combobox"
          aria-expanded={showPanel}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={activeId}
          placeholder="Search drivers, teams, circuits"
          autoComplete="off"
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            setOpen(true);
            if (e.target.value.trim().length < MIN_QUERY_LENGTH) {
              setStatus("idle");
              setGroups([]);
            }
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
          className="t-fast h-10 w-full rounded-md border border-line bg-surface pl-9 pr-8 text-sm placeholder:text-muted hover:border-muted"
        />
        <kbd
          aria-hidden="true"
          className="pointer-events-none absolute right-2.5 top-1/2 hidden -translate-y-1/2 rounded border border-line px-1.5 text-xs text-muted md:block"
        >
          /
        </kbd>
        <div
          id={listId}
          role="listbox"
          aria-label="Search suggestions"
          hidden={!showPanel}
          className="absolute left-0 right-0 top-full z-40 mt-1 max-h-[70vh] min-w-72 overflow-y-auto rounded-lg border border-line bg-surface p-1 shadow-lg sm:left-auto sm:w-96"
        >
          {status === "loading" && groups.length === 0 && (
            <p role="presentation" className="px-3 py-2 text-sm text-muted">
              Searching…
            </p>
          )}
          {status === "error" && (
            <p role="presentation" className="px-3 py-2 text-sm text-danger">
              Search is unavailable right now.
            </p>
          )}
          {status === "ready" && groups.length === 0 && (
            <p role="presentation" className="px-3 py-2 text-sm text-muted">
              No matches for “{query}”.
            </p>
          )}
          {groups.map((g, gi) => (
            <div key={g.key} role="group" aria-labelledby={`${id}-g-${g.key}`}>
              <div
                id={`${id}-g-${g.key}`}
                role="presentation"
                className="px-3 pb-1 pt-2 text-xs font-bold uppercase tracking-wide text-muted"
              >
                {g.label}
              </div>
              {g.items.map((item, ii) => {
                const selected = offsets[gi] + ii === active;
                return (
                  <div
                    key={item.id}
                    id={`${id}-opt-${item.id}`}
                    role="option"
                    aria-selected={selected}
                    // mousedown, not click: the input would blur and close the panel first.
                    onMouseDown={(e) => {
                      e.preventDefault();
                      go(item.href);
                    }}
                    className={`flex cursor-pointer items-baseline justify-between gap-3 rounded-md px-3 py-2 text-sm ${
                      selected ? "bg-accent-soft" : "hover:bg-surface-2"
                    }`}
                  >
                    <span className="font-semibold">{item.label}</span>
                    {item.detail && <span className="shrink-0 text-xs text-muted">{item.detail}</span>}
                  </div>
                );
              })}
            </div>
          ))}
          {searchable && groups.length > 0 && (
            <div
              role="presentation"
              className="border-t border-line px-3 py-2 text-xs text-muted"
            >
              Press Enter for all results
            </div>
          )}
        </div>
      </div>
      <p role="status" aria-live="polite" className="sr-only">
        {status === "ready" ? `${flat.length} suggestions` : ""}
      </p>
    </form>
  );
}
