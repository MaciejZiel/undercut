import { PageHeader } from "./page-header";
import { EmptyState } from "@/components/states/empty-state";

/** Stand-in for screens that are not built yet. */
export function PlaceholderPage({
  title,
  description,
  emptyTitle = "Nothing here yet",
  emptyDescription = "This screen is being built. Check back soon.",
}: {
  title: string;
  description: string;
  emptyTitle?: string;
  emptyDescription?: string;
}) {
  return (
    <>
      <PageHeader title={title} description={description} />
      <EmptyState
        title={emptyTitle}
        description={emptyDescription}
        action={{ label: "Back to the home page", href: "/" }}
      />
    </>
  );
}
