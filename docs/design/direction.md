# Visual direction

A bright, photographic race-weekend companion. The first screen answers "when is the next session and what happened last" before it asks anyone to explore a database. The direction comes from a design study (white, cool blue, navy, a serif for titles) that was moved into the real components; this note records the decisions that are not obvious from the code.

## Palette (tokens in `frontend/src/app/globals.css`)

| token | light | dark | use |
|---|---|---|---|
| `--bg` | #ffffff | #0f1826 | page |
| `--surface` | #f0f5fc | #162235 | schedule card, summary strip, table header, empty states |
| `--fg` | #203149 | #e8eef8 | text (13.2:1 on white) |
| `--fg-muted` | #5d6b7e | #9fb0c6 | secondary text (5.4:1 on white, 4.95:1 on surface) |
| `--accent` | #244d8e | #8fb4f0 | links, primary buttons, active tab (8.3:1 on white) |
| `--flag` | #f6dc89 | #e9cf7a | the prediction invitation and "preliminary" / "on now" flags only |
| `--positive` | #1f6b52 | #5fd0a3 | places gained |
| `--danger` | #a8322a | #ff8a80 | errors, places lost |

Team colours are data: a 3 px bar beside a name, never a panel colour.

## Type

Manrope for everything, DM Serif Display only for proper names: race names, driver, team and circuit names on their own pages, and the "this day in F1" sentence (`.display`). Section titles (`.heading`) are Manrope 800 at 20 to 22 px. Big figures (`.numeral`, countdown, stats) are Manrope 800 with tabular digits, so they read like timing. Labels are sentence case. Both fonts come through `next/font/google`, so there is no external request at runtime.

## Layout

Content width 1240 px, gutters 16 / 24 / 40 px. The home page is two columns (about 1.9 : 1) for the weekend, then two columns for the last race and the championship. Different information has different forms: the schedule is the one card (plus the yellow invitation), results are tables, the podium is a numbered list, the calendar is a hairline list grouped by month. Everything else sits on the page with hairlines, not in tinted panels. No rows of equal tiles. Radii are 8 px at most.

Result tables carry the information of a race: the gap column has a bar drawn to scale, laps down and retirements are words, and below 640 px the rows become two-line list items instead of scrolling sideways (`table.stack` in `globals.css`). The round page has two levels of navigation: sessions, then views (Results, Positions, Lap times, Tyres, Pit stops, Weather, Race control, Replay). Old `?view=analysis` and `?view=strategy` links still work.

## Imagery

There is no photograph. The one picture of the site is the racing line of the circuit, drawn from OpenF1 car positions (`Circuit.outline`): different for every round, from the site's own data, and no licence to carry. It is a large line on a pale casing with the start and finish marked on the home page and the circuit page. A circuit without an outline shows no image; nothing pretends to be the track. (An earlier version used a CC BY-SA photograph of Circuit of the Americas; it was dropped because it was not a picture of the race next to it.)

## Deliberately left out

- Animations (the study lists proposals for later: a 120 to 160 ms opacity change on filters, nothing on entry).
- Day filter and time-zone picker on the home schedule: five rows fit, and the visitor's own zone is detected. The calendar keeps its "my zone / circuit time" switch.
- Fake insights and decorative graphics. "Biggest gains" on a race page is computed from the grid and the finish.
