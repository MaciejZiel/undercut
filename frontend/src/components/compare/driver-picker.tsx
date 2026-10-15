"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useId, useState, type KeyboardEvent } from "react";
import { createApiClient } from "@/lib/api/client";

export type PickedDriver = { slug: string; name: string };

const MIN_QUERY = 2;
const DEBOUNCE_MS = 250;
const MAX_OPTIONS = 8;

async function searchDrivers(q: string, signal: AbortSignal): Promise<PickedDriver[]> {
  const { data, response } = await createApiClient(window.location.origin).GET("/api/v1/search/", {
    params: { query: { q } },
    signal,
  });
  if (!response.ok || !data) throw new Error(`Search failed with status ${response.status}`);
  return data.drivers.slice(0, MAX_OPTIONS).map((d) => ({ slug: d.slug, name: d.name }));
}

/**
 * Driver picker backed by the search endpoint, following the ARIA combobox pattern
 * (editable input + listbox): arrows move, Home/End jump, Enter selects, Escape closes.
 */
export function DriverPicker({
  label,
  value,
  onSelect,
  disabledSlug,
}: {
  label: string;
  /** Currently chosen driver; the name may be unknown until the comparison has loaded. */
  value: { slug: string; name: string | null } | null;
  onSelect: (driver: PickedDriver) => void;
  /** The other side's driver: shown but not selectable. */
  disabledSlug?: string | null;
}) {
  const uid = useId();
  const listId = `${uid}-list`;
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [term, setTerm] = useState("");
  const [active, setActive] = useState(0);

  useEffect(() => {
    const timer = setTimeout(() => setTerm(text.trim()), DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [text]);

  const searchable = term.length >= MIN_QUERY;
  const query = useQuery({
    queryKey: ["compare-driver-search", term],
    queryFn: ({ signal }) => searchDrivers(term, signal),
    enabled: open && searchable,
    staleTime: 60_000,
  });
  const options = searchable ? (query.data ?? []) : [];
  const optionId = (i: number) => `${uid}-opt-${i}`;
  const isOff = (d: PickedDriver) => d.slug === disabledSlug;
  const current = value ? (value.name ?? value.slug) : "";

  function close() {
    setOpen(false);
    setText("");
    setTerm("");
  }

  function choose(d: PickedDriver | undefined) {
    if (!d || isOff(d)) return;
    onSelect(d);
    close();
  }

  function move(delta: number) {
    if (options.length === 0) return;
    let i = active;
    for (let step = 0; step < options.length; step++) {
      i = (i + delta + options.length) % options.length;
      if (!isOff(options[i])) break;
    }
    setActive(i);
  }

  function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        if (!open) setOpen(true);
        else move(1);
        break;
      case "ArrowUp":
        e.preventDefault();
        if (!open) setOpen(true);
        else move(-1);
        break;
      case "Home":
        if (open && options.length) {
          e.preventDefault();
          setActive(0);
        }
        break;
      case "End":
        if (open && options.length) {
          e.preventDefault();
          setActive(options.length - 1);
        }
        break;
      case "Enter":
        if (open) {
          e.preventDefault();
          choose(options[active]);
        }
        break;
      case "Escape":
        if (open) {
          e.preventDefault();
          close();
        }
        break;
      case "Tab":
        close();
        break;
    }
  }

  let status: string | null = null;
  if (open) {
    if (!searchable) status = `Type at least ${MIN_QUERY} letters to search.`;
    else if (query.isError) status = "Search is unavailable. Try again.";
    else if (query.isPending || term !== text.trim()) status = "Searching…";
    else if (options.length === 0) status = "No driver matches.";
  }

  return (
    <div className="relative">
      <label htmlFor={`${uid}-input`} className="mb-1 block text-sm font-semibold">
        {label}
      </label>
      <input
        id={`${uid}-input`}
        type="text"
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={open && options.length > 0 ? optionId(active) : undefined}
        autoComplete="off"
        spellCheck={false}
        placeholder="Search a driver"
        value={open ? text : current}
        onFocus={() => setOpen(true)}
        onClick={() => setOpen(true)}
        onBlur={close}
        onChange={(e) => {
          setText(e.target.value);
          setActive(0);
          setOpen(true);
        }}
        onKeyDown={onKeyDown}
        className="w-full rounded-sm border border-line bg-surface px-3 py-2 text-sm"
      />
      {open && (
        <ul
          id={listId}
          role="listbox"
          aria-label={label}
          onMouseDown={(e) => e.preventDefault()}
          className="absolute z-20 mt-1 max-h-64 w-full overflow-y-auto rounded-sm border border-line bg-surface py-1 shadow-lg"
        >
          {status && (
            <li role="presentation" className="px-3 py-2 text-sm text-muted">
              {status}
            </li>
          )}
          {options.map((d, i) => {
            const off = isOff(d);
            return (
              <li
                key={d.slug}
                id={optionId(i)}
                role="option"
                aria-selected={d.slug === value?.slug}
                aria-disabled={off || undefined}
                onClick={() => choose(d)}
                onMouseMove={() => !off && setActive(i)}
                className={`flex cursor-pointer items-center justify-between gap-2 px-3 py-2 text-sm ${i === active ? "bg-accent-soft" : ""} ${off ? "cursor-not-allowed text-muted" : ""}`}
              >
                <span>{d.name}</span>
                {off && <span className="text-xs">already selected</span>}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
