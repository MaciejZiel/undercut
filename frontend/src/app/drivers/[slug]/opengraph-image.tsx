import { getDriver } from "@/lib/api/queries";
import { fullName } from "@/lib/format";
import { OG_CONTENT_TYPE, OG_SIZE, ogCard } from "@/lib/og";
import { isSlug } from "@/lib/url";

export const alt = "Driver profile on Undercut";
export const size = OG_SIZE;
export const contentType = OG_CONTENT_TYPE;

export default async function Image({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  // A failing API must not break the card: fall back to a generic one.
  const driver = isSlug(slug) ? await getDriver(slug).catch(() => null) : null;
  if (!driver) return ogCard({ eyebrow: "Driver", title: "Driver profile" });
  const { stats } = driver;
  return ogCard({
    eyebrow: "Driver",
    title: fullName(driver),
    subtitle: `${stats.starts} starts, ${stats.wins} wins, ${stats.podiums} podiums`,
  });
}
