import Link from "next/link";
import { SearchBox } from "@/components/layout/search-box";

export default function NotFound() {
  return (
    <section className="mx-auto flex max-w-xl flex-col items-start py-10">
      <p className="timing text-7xl font-extrabold tracking-tight text-accent sm:text-8xl">404</p>
      <h1 className="mt-2 text-3xl font-extrabold tracking-tight">There is no such corner</h1>
      <p className="mt-3 text-muted">
        You went off the track: this page does not exist or has moved. Search for what you were
        after, or head back to the pit lane.
      </p>
      <SearchBox className="mt-6 w-full" />
      <Link
        href="/"
        className="t-fast mt-5 rounded-sm bg-accent px-4 py-2 text-sm font-bold text-accent-fg hover:opacity-90"
      >
        Back to dashboard
      </Link>
    </section>
  );
}
