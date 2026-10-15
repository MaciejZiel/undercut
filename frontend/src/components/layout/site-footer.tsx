import Link from "next/link";
import { FOOTER_TEXT } from "@/lib/nav";
import { FooterCounts } from "@/components/dashboard/footer-counts";
import { Logo } from "./logo";

export function SiteFooter() {
  return (
    <footer className="mt-20 bg-surface">
      <div className="mx-auto w-full max-w-[77.5rem] px-4 pb-8 pt-10 sm:px-6 lg:px-10">
        <div className="flex flex-col gap-5 md:flex-row md:items-center md:gap-8">
          <Logo />
          <p className="text-sm text-muted">An independent place to follow Formula 1.</p>
          <nav aria-label="Footer" className="flex gap-6 text-sm font-semibold md:ml-auto">
            <Link href="/about" className="underline underline-offset-4 hover:text-accent">
              About and credits
            </Link>
            <Link href="/privacy" className="underline underline-offset-4 hover:text-accent">
              Privacy
            </Link>
          </nav>
        </div>
        <div className="mt-8 border-t border-line pt-5">
          <p className="max-w-3xl text-[0.8125rem] text-muted">{FOOTER_TEXT}</p>
          <FooterCounts />
        </div>
      </div>
    </footer>
  );
}
