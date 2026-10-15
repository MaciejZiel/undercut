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
          background: "#f2efe7",
          color: "#1d1e1b",
          fontFamily: "sans-serif",
          borderTop: "16px solid #b8341a",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", fontSize: 56, fontWeight: 900, color: "#1d1e1b", letterSpacing: -2, textTransform: "uppercase" }}>
          undercut
          <svg width="48" height="48" viewBox="0 0 24 24" style={{ marginLeft: 6 }}>
            <path d="M6 18 18 6M8 6h10v10" fill="none" stroke="#b8341a" strokeWidth="3.2" strokeLinecap="square" />
          </svg>
        </div>
        <div style={{ display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", fontSize: 30, fontWeight: 700, color: "#b8341a", textTransform: "uppercase", letterSpacing: 4 }}>
            {eyebrow}
          </div>
          <div style={{ display: "flex", fontSize: long ? 72 : 96, fontWeight: 900, lineHeight: 1.02, marginTop: 16, letterSpacing: -3, textTransform: "uppercase" }}>
            {title}
          </div>
          {subtitle ? (
            <div style={{ display: "flex", fontSize: 36, color: "#5a5851", marginTop: 20 }}>{subtitle}</div>
          ) : null}
        </div>
        <div style={{ display: "flex", fontSize: 26, color: "#5a5851" }}>
          Unofficial fan site. Not affiliated with Formula One Group or the FIA.
        </div>
      </div>
    ),
    { ...OG_SIZE },
  );
}
