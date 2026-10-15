type Outline = { width: number; height: number; points: number[][]; marker?: boolean };

const PAD = 40;
/** How much faster than real time the dot runs: a 1:36 record lap takes about ten seconds. */
export const RACER_SPEED = 10;

type Variant = "hero" | "mark";

/** Team-like colours for the cars; the order is shuffled per circuit. */
const CAR_COLORS = ["#3671c6", "#e8002d", "#27f4d2", "#ff8000", "#229971", "#64c4ff", "#6692ff", "#b6babd", "#ffd400", "#ff87bc"];
const CARS = 8;

function hash(text: string): number {
  let h = 2166136261;
  for (let i = 0; i < text.length; i++) h = Math.imul(h ^ text.charCodeAt(i), 16777619);
  return h >>> 0;
}

/** Small deterministic generator, so a circuit always gets the same field. */
function random(seed: number): () => number {
  let a = seed;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export type Car = { color: string; offset: number; pace: number };

/** The field of one circuit: eight cars in their own colours, spread along the lap, each a little faster or slower. */
export function carsFor(seed: string): Car[] {
  const rnd = random(hash(seed));
  const colors = [...CAR_COLORS].sort(() => rnd() - 0.5).slice(0, CARS);
  let gap = 0;
  return colors.map((color) => {
    gap += 0.025 + rnd() * 0.07;
    return { color, offset: gap, pace: 1 + (rnd() - 0.5) * 0.05 };
  });
}

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
  seed = null,
}: {
  outline: Outline;
  name: string;
  variant?: Variant;
  className?: string;
  /** Lap record in milliseconds: a dot then runs the lap at that pace, `speed` times faster. */
  lapMs?: number | null;
  speed?: number;
  /** Circuit slug: gives the circuit its own field of cars running the line. Without it no car is drawn. */
  seed?: string | null;
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
      {variant === "hero" && seed && (
        // SMIL, so the cars need no script; they appear once the line is drawn and are hidden for reduced motion.
        <g className="racer" aria-hidden="true">
          {carsFor(seed).map((car) => {
            const lap = Math.max(3, (lapMs ?? 88_000) / 1000 / speed);
            const dur = `${(lap * car.pace).toFixed(2)}s`;
            const begin = `${(2.6 - car.offset * lap).toFixed(2)}s`;
            return (
              <g key={car.color} opacity={0}>
                <set attributeName="opacity" to={1} begin="2.6s" fill="freeze" />
                {/* A short tail of the car's colour behind the head: a dash that slides along the line. */}
                <path d={path} pathLength={1} fill="none" stroke={car.color} strokeWidth={side * 0.007} strokeLinecap="round" strokeDasharray="0.04 2" strokeDashoffset={0.04} opacity={0.55}>
                  <animate attributeName="stroke-dashoffset" from="0.04" to="-0.96" dur={dur} begin={begin} repeatCount="indefinite" calcMode="linear" />
                </path>
                <g>
                  <circle r={side * 0.02} fill={car.color} opacity={0.2} />
                  <circle r={side * 0.0105} fill={car.color} stroke="var(--bg)" strokeWidth={side * 0.0035} />
                  <animateMotion path={path} dur={dur} begin={begin} repeatCount="indefinite" calcMode="linear" />
                </g>
              </g>
            );
          })}
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
