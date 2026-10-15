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

DM Serif Display (`.display` for page titles, `.heading` for section titles, `.numeral` for big figures) and Manrope for everything else, with tabular figures wherever digits line up (`.mono`, tables). Labels are sentence case. Both fonts come through `next/font/google`, so there is no external request at runtime.

## Layout

Content width 1240 px, gutters 16 / 24 / 40 px. The home page is two columns (about 1.9 : 1) for the weekend, then two columns for the last race and the championship. Different information has different forms: the schedule is a card, results are tables, the podium is a numbered list, the calendar is a hairline list. No rows of equal tiles.

## Photograph

One photograph: a grandstand at Circuit of the Americas (Earl McGehee, 2012, CC BY-SA 3.0). It sets the mood and is not a picture of the race next to it, so the caption always names the place. The credit links to `/about#credits`, which carries the licence and the font licences. The file is in `frontend/public/images/` and recorded in `3rdparty_licenses.md`.

## Deliberately left out

- Animations (the study lists proposals for later: a 120 to 160 ms opacity change on filters, nothing on entry).
- Day filter and time-zone picker on the home schedule: five rows fit, and the visitor's own zone is detected. The calendar keeps its "my zone / circuit time" switch.
- Fake insights and decorative graphics. "Biggest gains" on a race page is computed from the grid and the finish.
