type Outline = { width: number; height: number; points: number[][] };

const PAD = 40;

/**
 * The racing line of one lap, drawn from OpenF1 car positions. A wide pale stroke under a thin dark one reads
 * as tarmac; the yellow mark is the start and finish line.
 */
export function TrackOutline({ outline, name }: { outline: Outline; name: string }) {
  const width = outline.width + PAD * 2;
  const height = outline.height + PAD * 2;
  const pts = outline.points.map(([x, y]) => [x + PAD, y + PAD]);
  if (pts.length < 3) return null;
  const path = `M${pts.map(([x, y]) => `${x},${y}`).join(" L")}Z`;
  const [sx, sy] = pts[0];
  const [nx, ny] = pts[1];
  const angle = (Math.atan2(ny - sy, nx - sx) * 180) / Math.PI;
  return (
    <figure className="m-0">
      <svg
        role="img"
        aria-label={`Outline of ${name}`}
        viewBox={`0 0 ${width} ${height}`}
        className="h-auto w-full"
        style={{ maxHeight: "28rem" }}
      >
        <path d={path} fill="none" stroke="var(--line)" strokeWidth={34} strokeLinejoin="round" strokeLinecap="round" />
        <path d={path} fill="none" stroke="var(--fg)" strokeWidth={7} strokeLinejoin="round" strokeLinecap="round" />
        <g transform={`translate(${sx} ${sy}) rotate(${angle + 90})`}>
          <rect x={-20} y={-5} width={40} height={10} fill="var(--flag)" stroke="var(--fg)" strokeWidth={2} />
        </g>
      </svg>
      <figcaption className="mt-2 text-sm text-muted">Racing line of one lap, start and finish in yellow.</figcaption>
    </figure>
  );
}
