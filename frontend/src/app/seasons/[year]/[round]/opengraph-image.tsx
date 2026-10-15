import { getRound } from "@/lib/api/queries";
import { formatDate } from "@/lib/format";
import { OG_CONTENT_TYPE, OG_SIZE, ogCard } from "@/lib/og";
import { parseIntParam } from "@/lib/url";

export const alt = "Grand Prix results on Undercut";
export const size = OG_SIZE;
export const contentType = OG_CONTENT_TYPE;

export default async function Image({ params }: { params: Promise<{ year: string; round: string }> }) {
  const p = await params;
  const year = parseIntParam(p.year, { min: 1950, max: 2100 });
  const roundNo = parseIntParam(p.round, { max: 60 });
  const round = year && roundNo ? await getRound(year, roundNo).catch(() => null) : null;
  if (!round) return ogCard({ eyebrow: "Grand Prix", title: "Race results" });
  return ogCard({
    eyebrow: `Round ${round.round}`,
    title: `${round.year} ${round.name}`,
    subtitle: `${round.circuit.name}, ${formatDate(round.date)}`,
  });
}
