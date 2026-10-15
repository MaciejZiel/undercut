# Undercut — a race journal

## The job in five seconds

This is for the fan checking a weekend on a phone, the curious reader following a driver through history, and the enthusiast checking an explanation against lap data. It is a public reference, not a control room. Account features must not obstruct reading.

| Page | First answer | Next useful action |
| --- | --- | --- |
| Home | Where is the next race, when can I watch, who won last? | Open the weekend, save its schedule, check championship gaps |
| Standings / season matrix | Who leads, in which year and after which round? | Change the historical cutoff; follow an entrant or round |
| Driver / constructor | Who is this, what did they achieve? | Scan career totals, seasons and recent results; compare or follow |
| Circuit | Where is it, what races were held here? | Open a specific race; inspect location and history |
| Round | Which race and session am I reading, who finished where? | Switch session, then inspect laps, tyres or replay |
| Calendar | When is the next weekend in my time zone? | Find a round, save dates, switch to circuit time |
| Compare | Which two drivers and which period? | Pick both drivers, read aligned values and the meaning of a gap |
| Predictions / leagues | Can I still submit, what have I picked, where do I rank? | Enter picks; check lock time; open a league |
| Auth / settings | What information is required and why? | Complete one form; read field-specific feedback |
| Error / empty / loading | Is this absent, still loading, or unavailable? | Retry or take a useful route; never mistake missing data for zero |

## Visual idea

A race journal: a recognisable forest-green masthead over clear white reading surfaces, vermilion action marks and generous, sentence-case titles. Inspired by the organisation of a race programme: a weekend lead, compact classification, season records and a quieter historical note. The character comes from composition and typography, not imitation sponsor graphics, racing stripes or giant position numbers. The bespoke open U mark describes an inside line without copying a circuit or a racing logo.

The current timing-sheet treatment makes race titles shout, leaves large empty podium space and lets grey rules dominate. Replace that hierarchy. Home gives the weekend its own reading surface; the latest result is compact enough that the championship is reachable. Career statistics form a connected ledger. Tables sit on clean surfaces, with a small tinted header and row hover/focus tracking. Charts get room and a legible caption rather than decoration.

## Palette

Contrast ratios calculated using WCAG relative sRGB luminance; rounded to two decimals. Text uses the same pairs on every page. Team swatches are redundant with written names and are never text colours.

| Role | Light | Dark |
| --- | --- | --- |
| Page | #f2f5f2 | #17271f |
| Reading surface | #ffffff | #20352b |
| Secondary surface | #e5ede7 | #2b4437 |
| Text | #182e24 | #edf3ed |
| Secondary text | #52665a | #b5c8ba |
| Action / focus | #ad3e27 | #ffb29c |
| On action | #ffffff | #17271f |
| Selection | #e5ede7 | #304e3d |
| Schedule emphasis | #234b3a | #bfd4bd |
| On schedule emphasis | #ffffff | #17271f |
| Masthead, both themes | #234b3a with #ffffff text | #234b3a with #ffffff text |

The action is a restrained brick vermilion, not a luminous racing-red wash. Green gives the publication a stable identity while team colours remain small data marks. Dark mode uses lifted green surfaces rather than black and neon. Borders separate groups; they are not required to identify controls, whose background and labels remain visible.

## Type

IBM Plex Sans for body, navigation, names and tables: human, open and readable at 14–16 px. Barlow Condensed at 600/700 for page titles and prominent figures only, in sentence case. Its narrower proportions fit long race and driver names without all-capital shouting. IBM Plex Mono at 400/500 for lap times, gaps and clocks only. All supplied through next/font, with no runtime external font hosts.

Scale: 12 px secondary metadata, 14 px dense data/navigation, 16 px body, 20–24 px section headings, 32–48 px page names, 40–64 px weekend title. Body line height 1.5; titles 1.05–1.1. Tables use tabular numerals. Labels use sentence case; no ubiquitous uppercase eyebrows. Long headings wrap naturally and never depend on clipping.

## Layout and data

4 px base rhythm: 8/12 within controls, 16/24 within groups, 32/48 between sections. Maximum reading width 1248 px, with 20 px phone gutters and 32 px desktop gutters. Align titles, filters and results to the same left edge. Use asymmetry when content warrants it, not a repeated equal-card grid. Corners 4 px for controls, 8 px for a major reading panel; no ambient shadows. A selected tab has both a shape/background and a text/ARIA state.

At 390 px, schedule and titles stack, action links wrap and mobile navigation stays reachable. Dense tables scroll inside a named, keyboard-focusable region; the page itself must not scroll sideways. Numeric columns align right. Never use colour alone for position changes, rank, fastest lap, chart series or team identity. Keep semantic captions, row headers and sorting states. Do not invent data or imply a graphic is an actual circuit map.

Charts: theme-aware tokens, distinct categorical hues, textual legends and existing table alternatives. Keep tyre compounds semantic. Team colours identify entries but do not determine foreground contrast. Comparison emphasises the larger number with text weight and accessible text; explain when a smaller lap time is better.

## Motion and interaction

120 ms colour/border feedback only. No page-entry choreography, scroll pinning or count-up statistics. Existing replay is an explicitly controlled tool. Honour prefers-reduced-motion. Visible 2 px focus, at least 40 px controls (44 px on touch layouts), one h1 per page, retained skip link, labelled inputs, informative empty/loading/error states. Search keeps keyboard navigation and slash shortcut.

## Deliberately absent

No purple/blue gradients, cream/serif/terracotta editorial template, black/neon treatment, Inter, Space Grotesk, centred marketing layouts, feature-card triplets, floating shadows, glass, emoji, invented circuit drawings, logos or photos. No backend or route changes needed. Do not hide a functional weakness behind decoration.

## Inspection limits

Inspected supplied home, driver and round screenshots and their current implementations, shared navigation/data components, calendar, comparison, analytics, replay, predictions and form/state components. Live inspection is blocked in this execution environment: both wildcard and localhost binds on port 3100 fail with listen EPERM. Browser verification is a required follow-up, not a claimed result.
