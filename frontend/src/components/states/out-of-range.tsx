import { EmptyState } from "./empty-state";

/** A list page number beyond the last page (the API answers 404). */
export function PageOutOfRange({ firstPageHref }: { firstPageHref: string }) {
  return (
    <EmptyState
      title="No results on this page"
      description="This page is past the end of the list."
      action={{ label: "Back to the first page", href: firstPageHref }}
    />
  );
}
