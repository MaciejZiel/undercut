import { ImageResponse } from "next/og";

export const OG_SIZE = { width: 1200, height: 630 };
export const OG_CONTENT_TYPE = "image/png";

/**
 * Shared social card. No external fonts or images (system sans-serif and
 * inline shapes only), so it renders offline and at build time.
 */
export function ogCard({ eyebrow, title, subtitle }: { eyebrow: string; title: string; subtitle?: string }) {
  const long = title.length > 28;
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: 72,
          background: "#0b0f19",
          color: "#e8ecf5",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", fontSize: 40, fontWeight: 800 }}>
          <div style={{ width: 56, height: 12, background: "#b99cff", marginRight: 20, display: "flex" }} />
          Undercut
        </div>
        <div style={{ display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", fontSize: 32, color: "#b99cff", textTransform: "uppercase", letterSpacing: 4 }}>
            {eyebrow}
          </div>
          <div style={{ display: "flex", fontSize: long ? 72 : 96, fontWeight: 800, lineHeight: 1.05, marginTop: 16 }}>
            {title}
          </div>
          {subtitle ? (
            <div style={{ display: "flex", fontSize: 36, color: "#9ba8c1", marginTop: 20 }}>{subtitle}</div>
          ) : null}
        </div>
        <div style={{ display: "flex", fontSize: 26, color: "#9ba8c1" }}>
          Unofficial fan site. Not affiliated with Formula One Group or the FIA.
        </div>
      </div>
    ),
    { ...OG_SIZE },
  );
}
