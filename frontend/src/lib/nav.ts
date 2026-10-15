export type NavItem = {
  href: string;
  label: string;
  /** Path prefixes that mark this item as the current section. */
  match: string[];
  icon: "dashboard" | "calendar" | "standings" | "catalog" | "predict";
};

export const CATALOG_LINKS = [
  { href: "/drivers", label: "Drivers", hint: "Every driver since 1950" },
  { href: "/constructors", label: "Constructors", hint: "Teams and their history" },
  { href: "/circuits", label: "Circuits", hint: "Tracks and their winners" },
  { href: "/seasons", label: "Seasons", hint: "Year by year" },
] as const;

export const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Home", match: [], icon: "dashboard" },
  { href: "/calendar", label: "Calendar", match: ["/calendar"], icon: "calendar" },
  { href: "/standings/drivers", label: "Standings", match: ["/standings"], icon: "standings" },
  {
    href: "/catalog",
    label: "Catalog",
    match: ["/catalog", "/drivers", "/constructors", "/circuits", "/seasons"],
    icon: "catalog",
  },
  { href: "/predict", label: "Predict", match: ["/predict", "/leagues"], icon: "predict" },
];

export function isActive(item: NavItem, pathname: string): boolean {
  if (item.href === "/") return pathname === "/";
  return item.match.some((m) => pathname === m || pathname.startsWith(`${m}/`));
}

export const FOOTER_TEXT =
  "Unofficial fan site. Not affiliated with Formula One Group or the FIA. Data: Jolpica-F1, OpenF1.";
