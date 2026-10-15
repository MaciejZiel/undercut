"use client";

import { useId, useMemo, useRef, useState } from "react";
import type { PickableDriver } from "@/lib/predict/api";

function fold(s: string): string {
  return s.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

export function filterDrivers(drivers: PickableDriver[], query: string): PickableDriver[] {
  const q = fold(query.trim());
  if (!q) return drivers;
  return drivers.filter((d) => fold(d.name).includes(q) || (d.code != null && fold(d.code).includes(q)) || String(d.number ?? "") === q);
}

/**
 * Searchable driver picker following the ARIA combobox pattern (editable input + listbox):
 * ArrowUp/Down move, Home/End jump, Enter selects, Escape closes, typing filters.
 * Drivers in `disabledIds` stay visible but cannot be chosen (podium duplicates).
 */
export function DriverCombobox({
  label,
  drivers,
  value,
  onChange,
  disabledIds,
  disabled = false,
  error,
}: {
  label: string;
  drivers: PickableDriver[];
  value: number | null;
  onChange: (id: number) => void;
  disabledIds?: ReadonlySet<number>;
  disabled?: boolean;
  error?: string;
}) {
  const uid = useId();
  const listId = `${uid}-list`;
  const errId = `${uid}-err`;
  const inputRef = useRef<HTMLInputElement>(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);

  const selected = drivers.find((d) => d.id === value) ?? null;
  const shown = useMemo(() => filterDrivers(drivers, query), [drivers, query]);
  const isDisabled = (d: PickableDriver) => disabledIds?.has(d.id) ?? false;
  const optionId = (i: number) => `${uid}-opt-${i}`;

  const display = open ? query : selected ? `${selected.name}${selected.code ? ` (${selected.code})` : ""}` : "";

  function openList() {
    if (disabled) return;
    if (!open) {
      setQuery("");
      const i = shown.findIndex((d) => d.id === value);
      setActive(i >= 0 ? i : 0);
      setOpen(true);
    }
  }

  function close() {
    setOpen(false);
    setQuery("");
  }

  function choose(d: PickableDriver | undefined) {
    if (!d || isDisabled(d)) return;
    onChange(d.id);
    close();
  }

  function move(delta: number) {
    if (shown.length === 0) return;
    let i = active;
    // Skip disabled entries; the iteration guard is the list length.
    for (let step = 0; step < shown.length; step++) {
      i = (i + delta + shown.length) % shown.length;
      if (!isDisabled(shown[i])) break;
    }
    setActive(i);
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        if (!open) openList();
        else move(1);
        break;
      case "ArrowUp":
        e.preventDefault();
        if (!open) openList();
        else move(-1);
        break;
      case "Home":
        if (open) {
          e.preventDefault();
          setActive(0);
        }
        break;
      case "End":
        if (open) {
          e.preventDefault();
          setActive(Math.max(0, shown.length - 1));
        }
        break;
      case "Enter":
        if (open) {
          e.preventDefault();
          choose(shown[active]);
        }
        break;
      case "Escape":
        if (open) {
          e.preventDefault();
          e.stopPropagation();
          close();
        }
        break;
      case "Tab":
        close();
        break;
    }
  }

  return (
    <div className="relative">
      <label htmlFor={`${uid}-input`} className="mb-1 block text-sm font-semibold">
        {label}
      </label>
      <input
        ref={inputRef}
        id={`${uid}-input`}
        type="text"
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={open && shown.length > 0 ? optionId(active) : undefined}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errId : undefined}
        autoComplete="off"
        spellCheck={false}
        disabled={disabled}
        placeholder="Search a driver"
        value={display}
        onFocus={openList}
        onClick={openList}
        onBlur={close}
        onChange={(e) => {
          setQuery(e.target.value);
          setActive(0);
          setOpen(true);
        }}
        onKeyDown={onKeyDown}
        className={`w-full rounded-md border bg-surface px-3 py-2 text-sm disabled:opacity-60 ${error ? "border-danger" : "border-line"}`}
      />
      {open && (
        <ul
          id={listId}
          role="listbox"
          aria-label={label}
          // mousedown must not blur the input before the click registers
          onMouseDown={(e) => e.preventDefault()}
          className="absolute z-20 mt-1 max-h-64 w-full overflow-y-auto rounded-md border border-line bg-surface py-1 shadow-lg"
        >
          {shown.length === 0 && <li className="px-3 py-2 text-sm text-muted">No driver matches.</li>}
          {shown.map((d, i) => {
            const off = isDisabled(d);
            return (
              <li
                key={d.id}
                id={optionId(i)}
                role="option"
                aria-selected={d.id === value}
                aria-disabled={off || undefined}
                onClick={() => choose(d)}
                onMouseMove={() => !off && setActive(i)}
                className={`flex cursor-pointer items-center justify-between gap-2 px-3 py-2 text-sm ${i === active ? "bg-accent-soft" : ""} ${off ? "cursor-not-allowed text-muted" : ""}`}
              >
                <span>
                  {d.name}
                  {d.code && <span className="timing ml-2 text-xs text-muted">{d.code}</span>}
                </span>
                {off && <span className="text-xs">already on the podium</span>}
                {!off && d.id === value && <span aria-hidden="true">✓</span>}
              </li>
            );
          })}
        </ul>
      )}
      {error && (
        <p id={errId} className="mt-1 text-sm text-danger">
          {error}
        </p>
      )}
    </div>
  );
}
