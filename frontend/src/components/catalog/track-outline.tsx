type Outline = { width: number; height: number; points: number[][]; marker?: boolean };

const PAD = 40;
/** How much faster than real time the dot runs: a 1:36 record lap takes about ten seconds. */
export const RACER_SPEED = 10;

type Variant = "hero" | "mark";

// Stroke widths as a share of the drawing's longest side, so the line keeps its weight at every size.
const STROKE = { hero: { line: 0.0075, casing: 0.034 }, mark: { line: 0.045, casing: 0 } } as const;

/**
 * The racing line of one lap, drawn from OpenF1 car positions. `hero` is a large line on a pale casing
 * (tarmac) with the start and finish line marked in yellow; `mark` is a small line for headings.
 * Without an outline nothing is drawn: no placeholder pretends to be the track.
 */
export function TrackOutline({
  outline,
  name,
  variant = "hero",
  className = "",
  lapMs = null,
  speed = RACER_SPEED,
}: {
  outline: Outline;
  name: string;
  variant?: Variant;
  className?: string;
  /** Lap record in milliseconds: a dot then runs the lap at that pace, `speed` times faster. */
  lapMs?: number | null;
  speed?: number;
}) {
  const width = outline.width + PAD * 2;
  const height = outline.height + PAD * 2;
  const pts = outline.points.map(([x, y]) => [x + PAD, y + PAD]);
  if (pts.length < 3) return null;
  const path = `M${pts.map(([x, y]) => `${x},${y}`).join(" L")}Z`;
  const [sx, sy] = pts[0];
  const [nx, ny] = pts[1];
  const angle = (Math.atan2(ny - sy, nx - sx) * 180) / Math.PI;
  const side = Math.max(width, height);
  const s = STROKE[variant];
  return (
    <svg
      role="img"
      aria-label={`Outline of ${name}`}
      viewBox={`0 0 ${width} ${height}`}
      className={`h-auto ${className}`}
      preserveAspectRatio="xMidYMid meet"
    >
      {variant === "hero" && (
        <path
          d={path}
          fill="none"
          stroke="color-mix(in srgb, var(--fg) 11%, transparent)"
          strokeWidth={side * s.casing}
          strokeLinejoin="round"
          strokeLinecap="round"
          className="fade-in"
        />
      )}
      <path
        d={path}
        pathLength={1}
        fill="none"
        stroke="var(--fg)"
        strokeWidth={side * s.line}
        strokeLinejoin="round"
        strokeLinecap="round"
        className={variant === "hero" ? "draw" : "draw-quick"}
      />
      {variant === "hero" && outline.marker !== false && lapMs != null && lapMs > 0 && (
        // SMIL, so the dot needs no script; it starts once the line is drawn and is hidden for reduced motion.
        <g className="racer" aria-hidden="true">
          {[
            { r: 2.4, opacity: 0.22, fill: "var(--accent)" },
            { r: 1, opacity: 1, fill: "var(--accent)" },
          ].map((dot) => (
            <circle key={dot.r} r={side * 0.0085 * dot.r} fill={dot.fill} opacity={0}>
              <set attributeName="opacity" to={dot.opacity} begin="2.6s" fill="freeze" />
              <animateMotion path={path} dur={`${Math.max(3, lapMs / 1000 / speed)}s`} begin="2.6s" repeatCount="indefinite" calcMode="linear" />
            </circle>
          ))}
        </g>
      )}
      {variant === "hero" && outline.marker !== false && (
        <g transform={`translate(${sx} ${sy}) rotate(${angle + 90})`} className="appear-late">
          <rect x={-side * 0.02} y={-side * 0.005} width={side * 0.04} height={side * 0.01} fill="var(--flag)" stroke="var(--fg)" strokeWidth={side * 0.002} />
        </g>
      )}
    </svg>
  );
}
