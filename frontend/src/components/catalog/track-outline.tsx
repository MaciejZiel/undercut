type Outline = { width: number; height: number; points: number[][] };

const PAD = 40;

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
}: {
  outline: Outline;
  name: string;
  variant?: Variant;
  className?: string;
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
        <path d={path} fill="none" stroke="var(--surface-2)" strokeWidth={side * s.casing} strokeLinejoin="round" strokeLinecap="round" />
      )}
      <path d={path} fill="none" stroke="var(--fg)" strokeWidth={side * s.line} strokeLinejoin="round" strokeLinecap="round" />
      {variant === "hero" && (
        <g transform={`translate(${sx} ${sy}) rotate(${angle + 90})`}>
          <rect x={-side * 0.02} y={-side * 0.005} width={side * 0.04} height={side * 0.01} fill="var(--flag)" stroke="var(--fg)" strokeWidth={side * 0.002} />
        </g>
      )}
    </svg>
  );
}
