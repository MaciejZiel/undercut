import Link from "next/link";
import { FOOTER_TEXT } from "@/lib/nav";
import { Logo } from "./logo";

const REPO = "https://github.com/MaciejZiel/undercut";

const LINKS: { href: string; label: string; external?: boolean }[] = [
  { href: "/about", label: "About and data sources" },
  { href: "/privacy", label: "Privacy" },
  { href: REPO, label: "Source code", external: true },
  { href: `${REPO}/issues`, label: "Report a mistake", external: true },
];

const link = "underline decoration-transparent decoration-2 underline-offset-4 hover:text-accent hover:decoration-accent";

export function SiteFooter() {
  return (
    <footer className="mt-20 border-t-4 border-fg">
      <div className="mx-auto w-full max-w-[77.5rem] px-4 pb-8 pt-8 sm:px-6 lg:px-10">
        <div className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
          <div>
            <Logo />
            <p className="mt-3 max-w-[26rem] text-sm leading-relaxed text-muted">
              An independent Formula 1 fan project: every race since 1950, lap by lap analysis from 2023, and a
              prediction game. No ads, no tracking.
            </p>
          </div>
          <nav aria-label="About the project">
            <ul className="flex flex-wrap gap-x-6 gap-y-1 text-sm font-semibold md:justify-end">
              {LINKS.map((l) => (
                <li key={l.href}>
                  {l.external ? (
                    <a href={l.href} rel="noopener noreferrer" className={`${link} inline-flex min-h-6 items-center`}>
                      {l.label} <span aria-hidden="true">&nbsp;↗</span>
                    </a>
                  ) : (
                    <Link href={l.href} className={`${link} inline-flex min-h-6 items-center`}>
                      {l.label}
                    </Link>
                  )}
                </li>
              ))}
            </ul>
          </nav>
        </div>
        <div className="mt-8 flex flex-col gap-3 border-t border-line pt-4 md:flex-row md:items-baseline md:justify-between">
          <p className="text-sm text-muted max-w-3xl">{FOOTER_TEXT}</p>
        </div>
      </div>
    </footer>
  );
}
