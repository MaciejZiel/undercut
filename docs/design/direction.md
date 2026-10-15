# Visual direction

A race-desk broadsheet. Warm paper, black ink, one red. Rules do the work boxes usually do: a heavy rule opens a section, hairlines separate rows, vertical rules split columns. The home page follows a design study (a giant wordmark, the next weekend with a big place name and a clock, the last race, the championship, one line from the archive and the prediction call); this note records the decisions that are not obvious from the code.

## Palette (tokens in `frontend/src/app/globals.css`)

| token | light | dark | use |
|---|---|---|---|
| `--bg` | #f2efe7 | #171814 | page |
| `--surface` | #e9e5d9 | #20221c | the few filled areas (skeletons, chart frames) |
| `--line` / `--line-strong` | #cbc7bc / #aaa79f | #34362f / #4a4c43 | row hairlines / control borders |
| `--fg` | #1d1e1b | #f2efe7 | text and heavy rules (14.6:1 on paper) |
| `--fg-muted` | #5a5851 | #a9a69c | secondary text (6.2:1 on paper) |
| `--accent` | #b8341a | #ff7a5c | what is next and what is active: the UP NEXT tag, links, the arrow, the big archive year (5.2:1 on paper, 4.7:1 on the surface, white on it 5.9:1) |
| `--positive` / `--danger` | #1f6b52 / #a8322a | #5fd0a3 / #ff8a80 | places gained / errors |

Team colours are data: a 3 px bar beside a name, never a panel colour.

## Type

Archivo only, in weights, plus IBM Plex Mono for small captions. `.display` is Archivo 900 in capitals, tracked tight (page titles, race and driver names, the place on the home page). `.heading` is Archivo 800 in sentence case (section titles). `.numeral` is Archivo 800 with tabular digits (positions, points, the clock). `.eyebrow` / `.label` is Plex Mono 11 px in capitals with letter-spacing, used for the caption above a section or a value and for table heads. Both fonts come through `next/font/google`, so there is no external request at runtime.

## Layout

Content width 1240 px, gutters 16 / 24 / 40 px. The home page is a grid cut by rules: masthead, then the weekend (a wide column and a 376 px column with the clock and the schedule, split by a vertical rule), then the last race and the championship, then the archive and the prediction call under a heavy rule. Everything else sits on the page with hairlines, not in tinted panels. Corners are square. No rows of equal tiles.

Result tables carry the information of a race: the gap column has a bar drawn to scale, laps down and retirements are words, and below 640 px the rows become two-line list items instead of scrolling sideways (`table.stack` in `globals.css`). The round page has two levels of navigation: sessions, then views (Results, Positions, Lap times, Tyres, Pit stops, Weather, Race control, Replay). Old `?view=analysis` and `?view=strategy` links still work.

## Imagery

There is no photograph. The one picture of the site is the racing line of the circuit, drawn from OpenF1 car positions (`Circuit.outline`): different for every round, from the site's own data, and no licence to carry. It sits in the weekend block on the home page, as a mark beside a race title and wide on the circuit page. A circuit without an outline shows no image; nothing pretends to be the track.

## Motion

Played once when a block first appears, never looped, and off for visitors who ask for reduced motion: sections and rows rise into place in reading order (`.rise`), the racing line is drawn like a lap (`.draw`), gap bars grow to their length (`.grow-x`), a switched table fades in (`.fade-in`). Every class starts from the visible end state, so nothing waits on a script and nothing stays hidden. No parallax, no counters, no animation on scroll.

## Deliberately left out

- Day filter and time-zone picker on the home schedule: five rows fit, and the visitor's own zone is detected. The calendar keeps its "my zone / circuit time" switch.
- Fake insights and decorative graphics. "Biggest gains" on a race page is computed from the grid and the finish.
