import type { Metadata } from "next";
import Link from "next/link";
import { PageHeader } from "@/components/ui/page-header";
import { DataTable, RowTh, Td, Th, Tr } from "@/components/ui/data-table";
import { pageMetadata } from "@/lib/seo";

export const metadata: Metadata = pageMetadata({
  title: "Privacy policy",
  description: "What personal data Undercut stores, why, for how long, and how to export or delete it.",
  path: "/privacy",
});

const REPO = "https://github.com/MaciejZiel/undercut";

const DATA = [
  { item: "E-mail address", why: "Sign-in, account verification, password reset and the opt-in race e-mail." },
  { item: "Display name", why: "Shown next to your picks on leaderboards and in private leagues." },
  { item: "Password (stored only as a salted hash)", why: "Signing in. The plain password is never stored." },
  { item: "Preferences (theme, e-mail opt-in)", why: "Remembering your settings." },
  { item: "Favourites (drivers, teams, circuits)", why: "Showing them on your pages." },
  { item: "Predictions and league membership", why: "Running the prediction game and scoring it." },
] as const;

const link = "font-semibold text-accent underline underline-offset-4 hover:no-underline";
const h2 = "mb-3 text-xl font-extrabold tracking-tight";

export default function PrivacyPage() {
  return (
    <>
      <PageHeader
        title="Privacy policy"
        description="Plain language: what we keep, why, and how you stay in control."
        breadcrumbs={[{ label: "Privacy" }]}
      />
      <div className="flex max-w-3xl flex-col gap-10">
        <p role="note" className="rounded-lg border border-accent bg-accent-soft p-4 font-semibold">
          This policy is a template and still has to be reviewed by the site owner before it is relied upon.
        </p>

        <section aria-labelledby="who-h">
          <h2 id="who-h" className={h2}>
            Who is responsible
          </h2>
          <p>
            The controller of your personal data is the owner of this site, who can be reached through the{" "}
            <a className={link} href={`${REPO}/issues`} rel="noopener noreferrer">
              GitHub repository
            </a>
            . Undercut is a non-commercial hobby project run on a self-hosted server.
          </p>
        </section>

        <section aria-labelledby="data-h">
          <h2 id="data-h" className={h2}>
            What we collect and why
          </h2>
          <p className="mb-3">
            Browsing the site needs no account and stores nothing about you. If you create an account, we keep:
          </p>
          <DataTable caption="Personal data kept for an account and the purpose of each item" minWidth="20rem">
            <thead>
              <tr>
                <Th>Data</Th>
                <Th>Purpose</Th>
              </tr>
            </thead>
            <tbody>
              {DATA.map((row) => (
                <Tr key={row.item}>
                  <RowTh>{row.item}</RowTh>
                  <Td>{row.why}</Td>
                </Tr>
              ))}
            </tbody>
          </DataTable>
          <p className="mt-3 text-muted">
            The legal basis is performing the service you asked for (your account and the game) and, for the race
            e-mail, your consent, which you can withdraw at any time.
          </p>
        </section>

        <section aria-labelledby="cookies-h">
          <h2 id="cookies-h" className={h2}>
            Cookies and tracking
          </h2>
          <p>
            There are no tracking cookies, no analytics and no advertising. The only cookies are the session cookie
            and the CSRF cookie, which are strictly needed to keep you signed in and to protect forms. Your theme
            choice is kept in your own browser storage and never sent to us.
          </p>
        </section>

        <section aria-labelledby="email-h">
          <h2 id="email-h" className={h2}>
            E-mail
          </h2>
          <p>
            We send e-mail only for address verification, password reset and, if you switch it on in{" "}
            <Link className={link} href="/settings">
              settings
            </Link>
            , the race e-mail with your prediction score. Every race e-mail has a one-click unsubscribe link.
          </p>
        </section>

        <section aria-labelledby="keep-h">
          <h2 id="keep-h" className={h2}>
            How long we keep it
          </h2>
          <p>
            Account data is kept while your account exists and removed when you delete it. Backups of the database are kept for at most 30 days, so deleted data disappears from backups
            within that time. Public statistics (results, standings) are not personal data and are kept.
          </p>
        </section>

        <section aria-labelledby="control-h">
          <h2 id="control-h" className={h2}>
            Export and delete your account
          </h2>
          <p>
            You can download a copy of your data and delete your account at any time in{" "}
            <Link className={link} href="/settings">
              settings
            </Link>
            . Deleting removes your profile, favourites and predictions.
          </p>
        </section>

        <section aria-labelledby="rights-h">
          <h2 id="rights-h" className={h2}>
            Your rights under the GDPR
          </h2>
          <p>
            You have the right to access your data, to have it corrected or erased, to restrict or object to its
            processing, to receive it in a portable format and to withdraw consent. To use a right that settings
            does not cover, open an issue on the{" "}
            <a className={link} href={`${REPO}/issues`} rel="noopener noreferrer">
              GitHub issues page
            </a>{" "}
            without including personal details. You may also complain to your national data protection authority
            (in Poland, the President of the Personal Data Protection Office, UODO).
          </p>
        </section>
      </div>
    </>
  );
}
