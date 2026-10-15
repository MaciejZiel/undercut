import { Suspense } from "react";
import { Logo } from "./logo";
import { MainNav } from "./main-nav";
import { SearchBox } from "./search-box";
import { ThemeToggle } from "./theme-toggle";
import { AccountButton } from "./account-button";
import { UnverifiedBanner } from "@/components/account/unverified-banner";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-bg">
      <div className="mx-auto flex h-16 w-full max-w-7xl items-center gap-2 px-4 md:gap-4">
        <Logo />
        <div className="md:ml-4">
          <Suspense fallback={null}>
            <MainNav />
          </Suspense>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <SearchBox className="hidden w-72 sm:block md:w-56 xl:w-72" />
          <ThemeToggle />
          <AccountButton />
        </div>
      </div>
      {/* Mobile: search sits under the logo row so nothing overflows at 360 px. */}
      <SearchBox className="px-4 pb-3 sm:hidden" />
      <UnverifiedBanner />
    </header>
  );
}
