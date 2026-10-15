"use client";

import { usePathname } from "next/navigation";
import { Logo } from "./logo";

/** The home page has its own giant wordmark, so there the header carries the tagline instead of a second logo. */
export function HeaderBrand() {
  const home = usePathname() === "/";
  return (
    <>
      <Logo className={home ? "md:hidden" : ""} />
      {home && <p className="eyebrow hidden md:block">Independent Formula 1 intelligence</p>}
    </>
  );
}
