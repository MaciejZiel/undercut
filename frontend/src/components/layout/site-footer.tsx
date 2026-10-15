import { FOOTER_TEXT } from "@/lib/nav";
import { FooterCounts } from "@/components/dashboard/footer-counts";

export function SiteFooter() {
  return (
    <footer className="mt-16 border-t border-line">
      <p className="mx-auto max-w-7xl px-4 py-6 text-sm text-muted">{FOOTER_TEXT}</p>
      <div className="-mt-3">
        <FooterCounts />
      </div>
    </footer>
  );
}
