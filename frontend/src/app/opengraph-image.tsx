import { OG_CONTENT_TYPE, OG_SIZE, ogCard } from "@/lib/og";

export const alt = "Undercut: Formula 1 stats, race analytics and predictions";
export const size = OG_SIZE;
export const contentType = OG_CONTENT_TYPE;

export default function Image() {
  return ogCard({
    eyebrow: "Formula 1",
    title: "Stats, race analytics and predictions",
    subtitle: "Every race since 1950",
  });
}
