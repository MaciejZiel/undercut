import Link from "next/link";
import { FOOTER_TEXT } from "@/lib/nav";
import { FooterCounts } from "@/components/dashboard/footer-counts";
import { Logo } from "./logo";

const REPO = "https://github.com/MaciejZiel/undercut";

const COLUMNS: { title: string; links: { href: string; label: string; external?: boolean }[] }[] = [
  {
    title: "Follow the season",
    links: [
      { href: "/", label: "This weekend" },
      { href: "/calendar", label: "Calendar" },
      { href: "/standings/drivers", label: "Driver standings" },
      { href: "/standings/constructors", label: "Constructor standings" },
    ],
  },
  {
    title: "The archive",
    links: [
      { href: "/drivers", label: "Drivers" },
      { href: "/constructors", label: "Constructors" },
      { href: "/circuits", label: "Circuits" },
      { href: "/seasons", label: "Seasons since 1950" },
    ],
  },
  {
    title: "Play and compare",
    links: [
      { href: "/predict", label: "Prediction game" },
      { href: "/leagues", label: "Leagues" },
      { href: "/compare", label: "Compare drivers" },
      { href: "/login", label: "Sign in" },
    ],
  },
  {
    title: "The project",
    links: [
      { href: "/about", label: "About and credits" },
      { href: "/privacy", label: "Privacy" },
      { href: REPO, label: "Source code", external: true },
      { href: `${REPO}/issues`, label: "Report a mistake", external: true },
    ],
  },
];

const link = "underline decoration-transparent decoration-2 underline-offset-4 hover:text-accent hover:decoration-accent";

export function SiteFooter() {
  return (
    <footer className="mt-20 border-t-4 border-fg">
      <div className="mx-auto w-full max-w-[77.5rem] px-4 pb-8 pt-8 sm:px-6 lg:px-10">
        <div className="grid gap-x-10 gap-y-8 md:grid-cols-[1.3fr_repeat(4,minmax(0,1fr))]">
          <div className="md:pr-6">
            <Logo />
            <p className="mt-3 max-w-[22rem] text-sm leading-relaxed text-muted">
              An independent Formula 1 fan project: every race since 1950, lap by lap analysis from 2023, and a
              prediction game. No ads, no tracking.
            </p>
          </div>
          {COLUMNS.map((col) => (
            <nav key={col.title} aria-label={col.title}>
              <p className="eyebrow mb-3">{col.title}</p>
              <ul className="space-y-2 text-sm font-semibold">
                {col.links.map((l) => (
                  <li key={l.href}>
                    {l.external ? (
                      <a href={l.href} rel="noopener noreferrer" className={link}>
                        {l.label} <span aria-hidden="true">↗</span>
                      </a>
                    ) : (
                      <Link href={l.href} className={link}>
                        {l.label}
                      </Link>
                    )}
                  </li>
                ))}
              </ul>
            </nav>
          ))}
        </div>
        <div className="mt-10 flex flex-col gap-3 border-t border-line pt-4 md:flex-row md:items-baseline md:justify-between">
          <p className="eyebrow max-w-3xl normal-case tracking-normal">{FOOTER_TEXT}</p>
          <FooterCounts />
        </div>
      </div>
    </footer>
  );
}
