import Link from "next/link";
import { FOOTER_TEXT } from "@/lib/nav";
import { FooterCounts } from "@/components/dashboard/footer-counts";

export function SiteFooter() {
  return (
    <footer className="mt-16 border-t border-line bg-surface">
      <div className="mx-auto flex max-w-7xl flex-wrap items-start justify-between gap-6 px-5 py-8 md:px-8">
        <div>
          <p className="display text-2xl font-bold">undercut</p>
          <p className="mt-1 text-sm text-muted">The race, in context.</p>
        </div>
        <nav aria-label="Footer" className="flex flex-wrap gap-x-6 gap-y-3 text-sm font-semibold">
          <Link href="/compare" className="hover:underline">Compare drivers</Link>
          <Link href="/seasons" className="hover:underline">Season archive</Link>
          <Link href="/about" className="hover:underline">About &amp; sources</Link>
          <Link href="/privacy" className="hover:underline">Privacy</Link>
        </nav>
      </div>
      <p className="mx-auto max-w-7xl px-5 pb-5 text-xs leading-relaxed text-muted md:px-8">{FOOTER_TEXT}</p>
      <FooterCounts />
    </footer>
  );
}
