import { DetailsDismiss } from "@/components/ui/details-dismiss";
import { siteUrl } from "@/lib/seo";
import { icsHref } from "./time";

/**
 * "Add to calendar" with a choice, no JavaScript needed: Google Calendar and any calendar app that
 * understands webcal subscribe to the live feed (so a changed session time follows on its own), and the
 * file download stays for everything else. Google and the apps fetch the feed from the public site address.
 */
export function AddToCalendar({
  year,
  round,
  label,
  srName,
  className = "",
  align = "left",
}: {
  year: number;
  round?: number | null;
  label: string;
  /** Appended to the label for screen readers, so many menus on one page stay distinguishable. */
  srName?: string;
  className?: string;
  align?: "left" | "right";
}) {
  const path = icsHref(year, round);
  const host = siteUrl().replace(/^https?:\/\//, "");
  const webcal = `webcal://${host}${path}`;
  const google = `https://calendar.google.com/calendar/r?cid=${encodeURIComponent(webcal)}`;
  const item = "t-fast block px-3 py-2 text-sm font-bold hover:bg-surface-2 hover:text-accent";
  return (
    <details className="group relative">
      <DetailsDismiss />
      <summary
        className={`t-fast flex cursor-pointer list-none items-baseline justify-between gap-3 text-sm font-bold hover:text-accent [&::-webkit-details-marker]:hidden ${className}`}
      >
        <span>
          {label}
          {srName && <span className="sr-only">: {srName}</span>}
        </span>
        <span aria-hidden="true" className="transition-transform group-open:rotate-180">
          ▾
        </span>
      </summary>
      <ul
        className={`absolute z-20 mt-1 w-64 border border-fg bg-bg shadow-[4px_4px_0_var(--fg)] ${align === "right" ? "right-0" : "left-0"}`}
      >
        <li>
          <a href={google} target="_blank" rel="noopener noreferrer" className={item}>
            Google Calendar
          </a>
        </li>
        <li className="border-t border-line">
          <a href={webcal} className={item}>
            Apple Calendar, Outlook and others
          </a>
        </li>
        <li className="border-t border-line">
          <a href={path} className={item}>
            Download the file (.ics)
          </a>
        </li>
      </ul>
    </details>
  );
}
