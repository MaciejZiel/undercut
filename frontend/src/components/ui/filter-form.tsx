import Link from "next/link";
import { FilterAutoSubmit } from "./filter-auto-submit";

export type FilterField =
  | {
      kind: "select";
      name: string;
      label: string;
      value: string;
      options: { value: string; label: string }[];
      allLabel?: string;
    }
  | {
      kind: "text" | "number";
      name: string;
      label: string;
      value: string;
      placeholder?: string;
      list?: string[];
      min?: number;
      max?: number;
    };

const control =
  "t-fast h-11 w-full rounded-md border border-line-strong bg-bg px-3 text-sm placeholder:text-muted hover:border-accent";

/**
 * Filters as a plain GET form: state lives in the URL, it works without
 * JavaScript, and changing a filter resets the page. `hidden` carries state
 * that is not a field (the current sort order).
 */
export function FilterForm({
  action,
  fields,
  hidden = {},
  resetHref,
  active,
}: {
  action: string;
  fields: FilterField[];
  hidden?: Record<string, string | undefined>;
  resetHref: string;
  active: boolean;
}) {
  return (
    <form
      method="get"
      action={action}
      aria-label="Filters"
      className="mb-5 grid grid-cols-1 items-end gap-3 sm:grid-cols-2 lg:grid-cols-[repeat(auto-fit,minmax(11rem,1fr))]"
    >
      <FilterAutoSubmit />
      {Object.entries(hidden).map(([k, v]) => (v ? <input key={k} type="hidden" name={k} value={v} /> : null))}
      {fields.map((f) => {
        const id = `filter-${f.name}`;
        return (
          <div key={f.name} className="flex min-w-0 flex-col gap-1">
            <label htmlFor={id} className="text-xs font-bold text-muted">
              {f.label}
            </label>
            {f.kind === "select" ? (
              <select id={id} name={f.name} defaultValue={f.value} className={control}>
                <option value="">{f.allLabel ?? "All"}</option>
                {f.options.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            ) : (
              <>
                <input
                  id={id}
                  name={f.name}
                  type={f.kind === "number" ? "number" : "search"}
                  inputMode={f.kind === "number" ? "numeric" : undefined}
                  defaultValue={f.value}
                  placeholder={f.placeholder}
                  min={f.min}
                  max={f.max}
                  list={f.list ? `${id}-list` : undefined}
                  autoComplete="off"
                  className={control}
                />
                {f.list && (
                  <datalist id={`${id}-list`}>
                    {f.list.map((o) => (
                      <option key={o} value={o} />
                    ))}
                  </datalist>
                )}
              </>
            )}
          </div>
        );
      })}
      <div className="flex items-center gap-2">
        <button
          type="submit"
          className="t-fast h-11 rounded-md bg-accent px-5 text-sm font-bold text-accent-fg hover:bg-accent-hover"
        >
          Apply
        </button>
        {active && (
          <Link href={resetHref} className="t-fast h-11 content-center px-2 text-sm font-bold text-accent underline underline-offset-4 hover:no-underline">
            Reset
          </Link>
        )}
      </div>
    </form>
  );
}
