import Link from "next/link";
import { SearchBox } from "@/components/layout/search-box";

export default function NotFound() {
  return (
    <section className="mx-auto flex max-w-xl flex-col items-start py-10">
      <p className="numeral text-8xl text-accent">404</p>
      <h1 className="display mt-2 text-4xl">There is no such corner</h1>
      <p className="mt-3 text-muted">
        You went off the track: this page does not exist or has moved. Search for what you were
        after, or head back to the pit lane.
      </p>
      <SearchBox className="mt-6 w-full" />
      <Link
        href="/"
        className="t-fast mt-5 inline-flex min-h-11 items-center rounded-md bg-accent px-5 py-2 text-sm font-bold text-accent-fg hover:bg-accent-hover"
      >
        Back to the home page
      </Link>
    </section>
  );
}
