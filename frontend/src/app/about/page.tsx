import type { Metadata } from "next";
import Link from "next/link";
import { PageHeader } from "@/components/ui/page-header";
import { DataTable, Td, Th, Tr } from "@/components/ui/data-table";
import { pageMetadata } from "@/lib/seo";

export const metadata: Metadata = pageMetadata({
  title: "About and sources",
  description: "What Undercut is, where its data comes from, how it is licensed and how far back each dataset goes.",
  path: "/about",
});

const REPO = "https://github.com/MaciejZiel/undercut";

const AVAILABILITY = [
  { data: "Race results", since: "1950" },
  { data: "Constructors and constructor standings", since: "1958" },
  { data: "Qualifying times", since: "1994", note: "Q1, Q2 and Q3 split from 2006" },
  { data: "Fastest laps ranked", since: "2004" },
  { data: "Sprint sessions", since: "2021" },
  { data: "Detailed analytics (laps, stints, pit stops, replay)", since: "2023" },
] as const;

const link = "font-semibold text-accent underline underline-offset-4 hover:no-underline";
const h2 = "mb-3 text-xl font-extrabold tracking-tight";

export default function AboutPage() {
  return (
    <>
      <PageHeader
        title="About and sources"
        description="Undercut is a free, unofficial Formula 1 statistics and prediction site."
        breadcrumbs={[{ label: "About" }]}
      />
      <div className="flex max-w-3xl flex-col gap-10">
        <section aria-labelledby="what-h">
          <h2 id="what-h" className={h2}>
            What Undercut is
          </h2>
          <p className="text-fg">
            Undercut lets you browse every driver, team, circuit and season since 1950, follow the current
            championship, look into race analytics and strategy, replay a race lap by lap and play a friendly
            prediction game with other fans. It is a hobby project, built to be fast, accessible and easy to read.
          </p>
        </section>

        <section aria-labelledby="notice-h">
          <h2 id="notice-h" className={h2}>
            Unofficial and non-commercial
          </h2>
          <p className="rounded-lg border border-line bg-surface p-4">
            Undercut is an unofficial fan site. It is not affiliated with, endorsed by or connected to Formula One
            Group, Formula 1, the FIA or any team or driver. It is non-commercial: there are no ads, no payments and
            no sponsored content. It does not use official logos, trademarks or driver photos.
          </p>
        </section>

        <section aria-labelledby="sources-h">
          <h2 id="sources-h" className={h2}>
            Data sources and licences
          </h2>
          <ul className="flex list-disc flex-col gap-3 pl-5">
            <li>
              <a className={link} href="https://github.com/jolpica/jolpica-f1" rel="noopener noreferrer">
                Jolpica-F1
              </a>{" "}
              provides the history since 1950 and the current results and standings. Its data is published under the
              Creative Commons Attribution-NonCommercial-ShareAlike 4.0 licence (CC BY-NC-SA 4.0). Data derived from
              it is shared under the same terms and is not used commercially.
            </li>
            <li>
              <a className={link} href="https://openf1.org" rel="noopener noreferrer">
                OpenF1
              </a>{" "}
              provides the detailed race analytics from 2023: laps, stints, pit stops, positions, intervals and
              weather. It is used for non-commercial purposes only and is credited here and in the footer of every
              page.
            </li>
          </ul>
          <p className="mt-3 text-muted">
            Championship tables are imported as published rather than recomputed, because historical points rules
            (dropped scores, shared drives, exclusions) cannot be reproduced from results alone. If you find a
            mistake, please report it, so it can be fixed at the source or corrected here.
          </p>
        </section>

        <section aria-labelledby="how-h">
          <h2 id="how-h" className={h2}>
            How it works
          </h2>
          <p>
            Undercut is one Django application and one Next.js site. After a session ends, a scheduler asks the
            data sources for the final results. Each step of the import writes a small event note in the same
            database transaction as the data it describes, so a fact is never saved without its note. A background
            worker reads those notes and reacts: it updates the standings, scores the predictions for that round,
            tells the website which cached pages are now out of date and sends the opt-in race e-mail exactly once.
            Because every step can be safely repeated, a failure in the middle simply retries instead of leaving
            half-updated numbers. The source code is public on{" "}
            <a className={link} href={REPO} rel="noopener noreferrer">
              GitHub
            </a>
            , including the architecture notes.
          </p>
          <p className="mt-3">
            The site runs on a self-hosted server, so brief maintenance windows are possible.
          </p>
        </section>

        <section aria-labelledby="fresh-h">
          <h2 id="fresh-h" className={h2}>
            Data freshness
          </h2>
          <p>
            Results are updated after every session, usually within a few hours of the chequered flag. Preliminary
            results are labelled as such until they become final. Sources occasionally correct results after the
            fact, and those corrections are picked up on the next import.
          </p>
        </section>

        <section aria-labelledby="avail-h">
          <h2 id="avail-h" className={h2}>
            Data availability by year
          </h2>
          <DataTable caption="First season for which each kind of data is available" minWidth="20rem">
            <thead>
              <tr>
                <Th>Data</Th>
                <Th>Available since</Th>
                <Th>Note</Th>
              </tr>
            </thead>
            <tbody>
              {AVAILABILITY.map((row) => (
                <Tr key={row.data}>
                  <Td>{row.data}</Td>
                  <Td className="timing">{row.since}</Td>
                  <Td className="text-muted">{"note" in row ? row.note : ""}</Td>
                </Tr>
              ))}
            </tbody>
          </DataTable>
        </section>

        <section aria-labelledby="contact-h">
          <h2 id="contact-h" className={h2}>
            Contact
          </h2>
          <p>
            For corrections, questions or bug reports, open an issue on the{" "}
            <a className={link} href={`${REPO}/issues`} rel="noopener noreferrer">
              GitHub issues page
            </a>
            . See also the <Link className={link} href="/privacy">privacy policy</Link>.
          </p>
        </section>
      </div>
    </>
  );
}
