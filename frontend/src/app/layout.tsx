import type { Metadata } from "next";
import { Archivo } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";
import { SiteHeader } from "@/components/layout/site-header";
import { SiteFooter } from "@/components/layout/site-footer";
import { MobileTabBar } from "@/components/layout/mobile-tab-bar";
import { THEME_INIT_SCRIPT } from "@/lib/theme";
import { Suspense } from "react";

const archivo = Archivo({ variable: "--font-archivo", subsets: ["latin"], display: "swap" });

export const metadata: Metadata = {
  title: { default: "Undercut", template: "%s | Undercut" },
  description: "Formula 1 stats, race analytics and predictions. Unofficial fan site.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    // suppressHydrationWarning: the inline script sets data-theme before hydration.
    <html lang="en" className={`${archivo.variable} h-full antialiased`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body className="flex min-h-full flex-col">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-50 focus:rounded-md focus:bg-accent focus:px-4 focus:py-2 focus:font-bold focus:text-accent-fg"
        >
          Skip to main content
        </a>
        <Providers>
          <SiteHeader />
          <main id="main" tabIndex={-1} className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 outline-none">
            {/* Breadcrumb-ready: pages render <PageHeader breadcrumbs={...} /> at the top. */}
            <Suspense fallback={null}>{children}</Suspense>
          </main>
          <SiteFooter />
          <Suspense fallback={null}>
            <MobileTabBar />
          </Suspense>
        </Providers>
      </body>
    </html>
  );
}
