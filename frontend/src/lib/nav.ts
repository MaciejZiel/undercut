export type NavChild = { href: string; label: string; hint: string };

export type NavItem = {
  href: string;
  label: string;
  /** Path prefixes that mark this item as the current section. */
  match: string[];
  icon: "dashboard" | "calendar" | "standings" | "catalog" | "predict";
  /** A group opens a menu on desktop; on mobile the item links to `href`. */
  children?: readonly NavChild[];
};

export const ARCHIVE_LINKS: readonly NavChild[] = [
  { href: "/drivers", label: "Drivers", hint: "Every driver since 1950" },
  { href: "/constructors", label: "Constructors", hint: "Teams and their history" },
  { href: "/circuits", label: "Circuits", hint: "Tracks and their winners" },
  { href: "/seasons", label: "Seasons", hint: "Year by year" },
  { href: "/compare", label: "Compare drivers", hint: "Two careers side by side" },
];

export const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Weekend", match: [], icon: "dashboard" },
  { href: "/calendar", label: "Calendar", match: ["/calendar"], icon: "calendar" },
  {
    href: "/standings/drivers",
    label: "Standings",
    match: ["/standings"],
    icon: "standings",
    children: [
      { href: "/standings/drivers", label: "Drivers", hint: "Championship points" },
      { href: "/standings/constructors", label: "Constructors", hint: "Team points" },
    ],
  },
  {
    href: "/catalog",
    label: "Archive",
    match: ["/catalog", "/drivers", "/constructors", "/circuits", "/seasons", "/compare"],
    icon: "catalog",
    children: ARCHIVE_LINKS,
  },
  {
    href: "/predict",
    label: "Predict",
    match: ["/predict", "/leagues"],
    icon: "predict",
    children: [
      { href: "/predict", label: "Next race", hint: "Pick the podium" },
      { href: "/predict/history", label: "My picks", hint: "Your results so far" },
      { href: "/predict/leaderboard", label: "Leaderboard", hint: "Who is ahead" },
      { href: "/leagues", label: "Leagues", hint: "Play against friends" },
    ],
  },
];

export function isActive(item: NavItem, pathname: string): boolean {
  if (item.href === "/") return pathname === "/";
  return item.match.some((m) => pathname === m || pathname.startsWith(`${m}/`));
}

export const FOOTER_TEXT =
  "Unofficial fan site. Not affiliated with Formula One Group or the FIA. Data: Jolpica-F1, OpenF1.";
