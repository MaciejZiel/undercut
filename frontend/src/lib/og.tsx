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
          background: "#f0f5fc",
          color: "#203149",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", fontSize: 44, fontWeight: 800, color: "#244d8e", letterSpacing: -2 }}>
          <div style={{ width: 52, height: 52, background: "#244d8e", borderRadius: 12, marginRight: 16, display: "flex" }} />
          undercut
        </div>
        <div style={{ display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", fontSize: 32, fontWeight: 700, color: "#244d8e" }}>
            {eyebrow}
          </div>
          <div style={{ display: "flex", fontSize: long ? 72 : 96, fontWeight: 800, lineHeight: 1.05, marginTop: 16, letterSpacing: -2 }}>
            {title}
          </div>
          {subtitle ? (
            <div style={{ display: "flex", fontSize: 36, color: "#5d6b7e", marginTop: 20 }}>{subtitle}</div>
          ) : null}
        </div>
        <div style={{ display: "flex", fontSize: 26, color: "#5d6b7e" }}>
          Unofficial fan site. Not affiliated with Formula One Group or the FIA.
        </div>
      </div>
    ),
    { ...OG_SIZE },
  );
}
