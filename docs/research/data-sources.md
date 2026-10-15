# Data sources: Jolpica-F1 and OpenF1

Verified 2026-10-15 against live responses and current docs. Anything not
verified is marked UNVERIFIED. Probe requests used the User-Agent
`Undercut/0.1 (research)`.

Sources:
- Jolpica docs: https://github.com/jolpica/jolpica-f1/tree/main/docs
  (`database_dumps.md`, `rate_limits.md`, `ergast_differences.md`,
  `endpoints/data/dumps.md`), `TERMS.md`
- Jolpica API: https://api.jolpi.ca/ergast/f1/ ; dumps: https://api.jolpi.ca/data/dumps/download/
- OpenF1: https://openf1.org/docs , https://openf1.org/auth.html

## 1. Jolpica database dump

**Verdict: usable. The "initial import from the CSV dump" plan works, with caveats below.**

| Item | Finding |
|---|---|
| Listing | `GET https://api.jolpi.ca/data/dumps/download/` returns JSON (`available_types`, `latest_dumps`, `delayed_dumps`, `delay_days`) with `file_hash` (SHA256), `file_size`, `uploaded_at`, `download_url` |
| Types | `csv` and `sql` (docs only mention csv; the live listing offers both) |
| Free download | `GET /data/dumps/download/delayed/?dump_type=csv` returns 302 to a pre-signed S3 URL (short expiry) for `jolpica-f1-csv.zip`. No login, no key. Use `curl -L` |
| Latest (no delay) | `/data/dumps/download/latest/` returns 401 `WWW-Authenticate: Token`: supporter tier, API key required |
| Delay | `delay_days` = 14. Delayed dump seen: uploaded 2026-09-26; latest: 2026-10-13 |
| Frequency | No published schedule. Observed gaps of about 2 weeks (docs example 2025-09-07 / 2025-09-21; live 09-26 / 10-13). Treat as irregular |
| Size | csv zip 14.5 MB (delayed), about 44 MB unpacked (`formula_one_lap.csv` is 36 MB). Docs example showed 6.6 MB (older, fewer data) |
| License | Docs/TERMS: data is CC BY-NC-SA 4.0, API "freely available for non-commercial use"; commercial use needs contact with admin@jolpi.ca. `database_dumps.md` says free dumps are non-commercial and supporter dumps are licensed for commercial use. The code repo is Apache-2.0 (code only, not data). Spec's CC BY-NC-SA claim is confirmed |
| Stability | Docs: column order may change, reference columns by name. Schema "not final" |

Delayed dump contents (downloaded and inspected), 18 CSVs, header row, UTF-8,
booleans as `t`/`f`, integer PKs plus `api_id` strings (`driver_NNme7ruE`).
Row counts are for the 2026-09-26 dump.

| Table (`formula_one_*.csv`) | Rows | Columns |
|---|---|---|
| season | 77 | id, api_id, championship_system_id, wikipedia, year |
| round | 1173 | id, api_id, circuit_id, date, is_cancelled, name, number, race_number, season_id, wikipedia |
| session | 5130 | id, api_id, has_time_data, is_cancelled, number, point_system_id, round_id, scheduled_laps, timestamp, timezone, type |
| sessionentry | 51549 | id, api_id, detail, fastest_lap_rank, grid, is_classified, is_eligible_for_points, laps_completed, points, position, round_entry_id, session_id, status, time |
| roundentry | 27641 | id, api_id, car_number, round_id, team_driver_id |
| teamdriver | 3630 | id, api_id, driver_id, role, season_id, team_id |
| driver | 881 | id, abbreviation, api_id, country_code, date_of_birth, forename, nationality, permanent_car_number, reference, surname, wikipedia |
| team | 214 | id, api_id, base_team_id, country_code, name, nationality, primary_color, reference, wikipedia |
| circuit | 78 | id, altitude, api_id, country, country_code, latitude, locality, longitude, name, reference, wikipedia |
| driverchampionship | 36570 | id, adjustment_type, driver_id, highest_finish, is_eligible, points, position, round_id, round_number, season_id, session_id, session_number, win_count, year |
| teamchampionship | 14436 | same shape with team_id instead of driver_id |
| lap | 731847 | id, api_id, average_speed, is_deleted, is_entry_fastest_lap, number, position, session_entry_id, time |
| pitstop | 12903 | id, api_id, duration, lap_id, local_timestamp, number, session_entry_id |
| pointsystem | 24 | id, api_id, driver_fastest_lap, driver_position_points, is_double_points, name, partial, reference, shared_drive, team_fastest_lap, team_position_points |
| championshipsystem | 11 | id, api_id, driver_best_results, driver_season_split, eligibility, name, reference, team_best_results, team_points_per_session, team_season_split |
| championshipadjustment | 3 | id, adjustment, api_id, driver_id, points, season_id, team_id |
| penalty, baseteam | 0 | (empty) |

Dump quirks relevant to the importer:
- Qualifying is stored as separate sessions `Q1`, `Q2`, `Q3` (2006+), `QB` (1994-2005 single session; also `QO` 2003-04, `QA` 2005), and sprint qualifying as `SQ1`-`SQ3` (2023+). `sessionentry.time` is EMPTY for all qualifying sessions. Qualifying times live in `lap` rows (`is_entry_fastest_lap = t`, `time` like `00:01:16.29`). The API instead returns one merged row with `Q1/Q2/Q3` strings. The spec's `Session.type = Q` and `QualifyingResult.q1_ms..q3_ms` need an explicit merge step.
- Session type codes seen: R, SR (sprint), QB, QO, QA, Q1-Q3, SQ1-SQ3, FP1-FP3.
- `sessionentry.status` is an integer code (0 = Finished, 1, 10, 11, 20, 30, 40...) and `detail` holds the text ("Finished", "+1 Lap", "Engine"). Both are empty for qualifying rows.
- `sessionentry.time` for races looks like `02:13:23.6` (h:mm:ss.f); `lap.time` like `00:01:16.29` (variable fractional digits); pitstop `duration` like `00:00:24.036`. Parse as intervals, not strings of fixed width.
- Standings are per round: `driverchampionship` (from 1950) and `teamchampionship` (from 1958) have one row per round and entity. This covers the whole standings backfill with no API calls. The 2026 data in the dump stops at round 15 (as of 2026-09-26).
- `round` keeps cancelled rounds (`is_cancelled = t`, `number` empty; example 2026 Saudi Arabian GP, id 1178). Future rounds of the current season are present (2026 rounds 21-23 dated Nov-Dec).
- `session.timestamp` for old sessions is a date at 00:00:00+00:00 (no real start time), plus an IANA `timezone` column.
- `circuit` has `altitude` and `country_code`; no length or lap record (spec is right that these are manual).
- `team.primary_color` exists (a possible seed for `ConstructorSeason.color_hex`; was empty in the first row, coverage UNVERIFIED).
- FP1-FP3 sessions and entries exist only for 2025-2026 in the dump (808 entries).
- IDs: `driver.reference` = API `driverId`; `team.reference` = `constructorId`; `circuit.reference` = `circuitId`.

Import flow: download the delayed zip, verify SHA256 against the listing
(`file_hash`), load by column name, then top up from the API for rounds newer
than the dump's last round (up to about 14 days plus a few rounds).

### Fallback: API-only resumable import (if the dump is unavailable)

Limits (`rate_limits.md`, unauthenticated): burst 4 req/s, sustained 500 req/h,
"will decrease in the future". 429 body: "Request was throttled." No headers
documented. The binding limit is 500/h, not 4/s. At 80% (400/h):

| Block | Requests (approx.) |
|---|---|
| static: seasons 1, circuits 1, drivers 9, constructors 3, status 2 | 16 |
| races (schedule) 1172 rounds / 100 | 12 |
| results, `/{year}/results/?limit=100` (about 27k rows) | about 280 |
| qualifying (1994+, about 14k rows) | about 140 |
| sprint (2021+) | about 8 |
| pit stops (2011+, 12.9k rows) | about 130 |
| driver standings per round (no all-rounds endpoint): 1172 | 1172 |
| constructor standings per round (1958+) | about 1100 |
| **Total** | **about 2,900** |

About 7.3 h at 400/h, 5.8 h at 500/h. Make it resumable (per-endpoint, per-season
cursor in SyncRun, persist raw responses), and honour 429 with backoff. Per-round
standings are 78% of the cost; the dump avoids all of it.

## 2. Jolpica API

Base `https://api.jolpi.ca/ergast/f1/`. Ergast-compatible, JSON only (no XML).
Trailing `/` or `.json` accepted. Responses carry `cache-control: max-age=600`
behind Cloudflare, so up to 10 min stale.

Endpoints (all verified live unless stated):
`/seasons/`, `/{year}/races/` (schedule; also `/races/` for all, total 1172),
`/{year}/{round}/results/`, `/qualifying/`, `/sprint/`, `/driverstandings/`,
`/constructorstandings/`, `/circuits/`, `/drivers/`, `/constructors/` (and
`/constructors/{id}/`), `/status/`, `/pitstops/`, `/laps/`. Ergast filter
chains (`/{year}/{round}/...`, `/drivers/{id}/results/`) are supported, UNVERIFIED
beyond the ones used here. Standings require a year (`ergast_differences.md`).
`/{year}/{round}/practice/` does not exist ("Endpoint does not support final
filter" is returned for a bogus path).

Pagination: `limit` default 30, max 100 (`?limit=500` returns `"limit":"100"`),
`offset` from 0. `MRData.total` is a string. A repeated filter keeps only the
last one (Ergast returned 400). Empty results return 200 with an empty list and
`total":"0"` (for example 1957 constructor standings).

Quirks and Ergast differences:
- Every number is a JSON string (`"position":"1"`, `"points":"26"`, `"lat":"26.0325"`, `total`, `limit`).
- `positionText` uses `R` instead of Ergast's `N` for retirements.
- `Time.time` always has 3 decimals; `Time.millis` is a string; for non-winners `time` is a gap (`+22.457`) while `millis` is the total.
- `points` includes the fastest-lap point where applicable (Verstappen 2024 R1: 26).
- `status` values changed; from 2025 all retirements and accidents are plain "Retired". `/status/` has 136 rows with counts.
- Optional fields are omitted, not null: `permanentNumber` and `code` missing for old drivers, `time` (race start) missing for old races, `Time` missing for lapped or retired drivers, `FastestLap` missing before 2004 (UNVERIFIED for every year), `Q2`/`Q3` missing when not set (1995 R1 has only `Q1`).
- Sprint Shootout / Sprint Qualifying naming in the race schedule is changed (2023: `SprintShootout`; 2024+: `SprintQualifying`).
- `/races/` schedule carries `FirstPractice`, `SecondPractice`, `ThirdPractice`, `Qualifying` (`{date,time}`), plus `Sprint` / `SprintQualifying` keys where applicable (the 2026 R1 sample had no sprint). Race start is top-level `date` + `time` (`Z`, UTC).
- 2026 data: `/2026/races/` total 23 (also see `is_cancelled` in the dump: an API-side view of cancelled rounds is UNVERIFIED).

Real examples (2024 round 1, `limit=1` or 2, trimmed):

Results `/2024/1/results/?limit=2`:
```json
{"MRData":{"limit":"2","offset":"0","total":"20","RaceTable":{"season":"2024","round":"1","Races":[{
 "season":"2024","round":"1","raceName":"Bahrain Grand Prix","date":"2024-03-02","time":"15:00:00Z",
 "Circuit":{"circuitId":"bahrain","circuitName":"Bahrain International Circuit",
   "Location":{"lat":"26.0325","long":"50.5106","locality":"Sakhir","country":"Bahrain"}},
 "Results":[{"number":"1","position":"1","positionText":"1","points":"26",
   "Driver":{"driverId":"max_verstappen","permanentNumber":"3","code":"VER","givenName":"Max","familyName":"Verstappen","dateOfBirth":"1997-09-30","nationality":"Dutch"},
   "Constructor":{"constructorId":"red_bull","name":"Red Bull","nationality":"Austrian"},
   "grid":"1","laps":"57","status":"Finished",
   "Time":{"millis":"5504742","time":"1:31:44.742"},
   "FastestLap":{"rank":"1","lap":"39","Time":{"time":"1:32.608"},"AverageSpeed":{"units":"kph","speed":"210.383"}}}]}]}}}
```
(`url` fields omitted for brevity.) Result rows carry the constructor of that
race, which is what the v2 model needs.

Qualifying `/2024/1/qualifying/?limit=1`: `"QualifyingResults":[{"number":"1","position":"1","Driver":{...},"Constructor":{...},"Q1":"1:30.031","Q2":"1:29.374","Q3":"1:29.179"}]`
(times are `m:ss.mmm` strings, no millis integers).

Driver standings `/2024/1/driverstandings/?limit=1`:
`"StandingsLists":[{"season":"2024","round":"1","DriverStandings":[{"position":"1","positionText":"1","points":"26","wins":"1","Driver":{...},"Constructors":[{"constructorId":"red_bull",...}]}]}]`
(`Constructors` is an array: a driver can have several teams in a season.)

Constructor standings: `"ConstructorStandings":[{"position":"1","positionText":"1","points":"44","wins":"1","Constructor":{"constructorId":"red_bull","name":"Red Bull","nationality":"Austrian"}}]`.

Sprint `/2024/5/sprint/`: `"SprintResults":[{... "grid":"4","laps":"19","Time":{"millis":"1924660","time":"32:04.660"},"FastestLap":{"rank":"1","lap":"3","Time":{"time":"1:40.331"}}}]` (no `AverageSpeed` here).

Pit stops `/2024/1/pitstops/`: `"PitStops":[{"driverId":"hulkenberg","lap":"1","stop":"1","time":"18:05:33","duration":"36.604"}]` (`time` is local wall clock of day).

Circuit: `{"circuitId":"adelaide","circuitName":"Adelaide Street Circuit","Location":{"lat":"-34.9272","long":"138.617","locality":"Adelaide","country":"Australia"}}`
(no country code, no length, no timezone).
Driver: `{"driverId":"adolff","givenName":"Kurt","familyName":"Adolff","dateOfBirth":"1921-11-05","nationality":"German"}`.
Season: `{"season":"1950","url":"..."}` (77 seasons, 1950-2026).
Status: `{"statusId":"1","count":"8191","status":"Finished"}`.

## 3. Field availability by season (spec table vs reality)

Checked from the dump (`formula_one_*`) and spot-checked on the API.

| Data | Spec | Reality | Verdict |
|---|---|---|---|
| Race results, driver standings | 1950 | 1950 (standings per round from 1950) | OK |
| Constructor standings | 1958 | 1958 (dump `teamchampionship` year min 1958; API 1957 empty, 1958 has 3 teams) | OK |
| Qualifying with times | 1994 | Session rows from 1994 (`QB`); API returns 1995 R1 with `Q1` only. 1990 R1 empty. Times only in `lap` rows in the dump. 1994 itself: dump has 391 laps; the API result for 1994 UNVERIFIED | OK with caveat: Q1/Q2/Q3 split only from 2006; 1994-2005 has a single time (`Q1`) |
| Pole position | 1950 via grid | Grid present from 1950 | OK |
| Lap times | 1996 | Dump has laps from 1994 but 1994-95 are sparse (about 390 rows per year); full coverage from 1996 (14.6k rows) | OK (full from 1996) |
| Fastest lap rank | 2004 | Present for 11 of 226 entries in 1958 (sparse, early years); dense from 2004 (347 of 360) | Correct to 2004 for reliable data; do not show 1958-2003 ranks as complete |
| Pit stops | 2011 | 2011 | OK |
| Sprints | 2021 | 2021 | OK |
| Sprint qualifying / shootout sessions | not listed | 2023 | Add |
| FP results in Jolpica | "FP results 2023, OpenF1" | Dump has FP1-FP3 entries from 2025 only (not exposed in the API as far as verified) | Spec should take FP from OpenF1 `session_result`; Jolpica FP is 2025+ and only in the dump |
| OpenF1 `stop_duration` | GP USA 2024 | Field doc says "from 2024 US GP onward"; Bahrain 2024 returned `stop_duration: null` | OK |

## 4. OpenF1

Base `https://api.openf1.org/v1/`. JSON default, `csv=true` for CSV. Filters:
`key=value`, `>`, `<`, `>=`, `<=` on any non-array field (`date<2024-03-02T15:02:00`),
`meeting_key=latest` / `session_key=latest`. An empty result returns HTTP 404
`{"detail":"No results found."}` (not 200 with `[]`): the client must treat this as empty.

Coverage: 2023 onward (verified: `meetings?year=2022` returns 404 no results). No
pre-2023 data.

Rate limits: not stated on openf1.org/docs or `/auth.html`. A web search result
states free tier 3 req/s and 30 req/min, sponsor tier 6 req/s and 60 req/min
(secondary source, UNVERIFIED on the official site); the spec's "3/s, 30/min"
matches. 429 on excess. Sponsor/authenticated: `POST https://api.openf1.org/token`
(form `username`, `password`) returns `access_token`, `expires_in` 3600, `token_type`
bearer; use `Authorization: Bearer`. Auth also unlocks real-time REST, MQTT and
WebSocket. Price: no price on the pages (spec's 9.90 EUR/month UNVERIFIED). Reports
that data from 30 min before to 30 min after a session is gated as live (UNVERIFIED).
License: none stated on the docs page or the GitHub README (the project calls itself
"free and open-source"). The spec's "CC BY-NC-SA 4.0" for OpenF1 is UNVERIFIED; the
repo README only names a LICENSE file, whose text I could not read. Disclaimer:
unofficial, F1 trademarks owned by Formula One Licensing B.V.

Verified live (session 9472 = 2024 Bahrain GP Race, meeting 1229), key fields:

| Endpoint | Fields (as returned) | Notes |
|---|---|---|
| `/meetings` | meeting_key, meeting_name, meeting_official_name, location, country_key/code/name, country_flag, circuit_key, circuit_short_name, circuit_type, circuit_info_url, circuit_image, gmt_offset, date_start, date_end, year, is_cancelled | `meetings` has no `session_key`. `is_cancelled` exists, so OpenF1 does mark cancellations |
| `/sessions` | session_key, session_type, session_name, date_start, date_end, meeting_key, circuit_key, ..., gmt_offset, year, is_cancelled | Race: `session_type` "Race", `session_name` "Race". Sprint, qualifying names: UNVERIFIED |
| `/drivers` | meeting_key, session_key, driver_number, broadcast_name, full_name, first_name, last_name, name_acronym (VER), team_name, team_colour (hex no `#`), headshot_url, country_code | per session; `country_code` deprecated, removal planned after 2026 |
| `/laps` | session_key, driver_number, lap_number, date_start, duration_sector_1/2/3, lap_duration (seconds, float), i1_speed, i2_speed, st_speed, is_pit_out_lap, segments_sector_1/2/3 | `date_start` approximate. Names differ from spec (`lap_duration`, not `duration_ms`; seconds, not ms) |
| `/stints` | session_key, stint_number, driver_number, lap_start, lap_end, compound (SOFT/MEDIUM/HARD...), tyre_age_at_start | matches spec |
| `/pit` | date, session_key, driver_number, lap_number, lane_duration, stop_duration, pit_duration | `stop_duration` null for 2024 R1; `pit_duration` duplicates `lane_duration`, deprecated |
| `/position` | date, session_key, driver_number, position | event-driven (first sample 14:03Z, an hour before the start): includes pre-session rows |
| `/intervals` | date, session_key, driver_number, gap_to_leader, interval | float, string ("+1 LAP") or null; races only |
| `/race_control` | date, session_key, driver_number (null), lap_number, category, flag, scope, sector, qualifying_phase, message | spec lacks `scope`, `sector`, `qualifying_phase`; `lap_number` can be null (UNVERIFIED) |
| `/weather` | date, session_key, air_temperature, track_temperature, humidity, pressure, wind_speed, wind_direction, rainfall (0/1) | 1/min |
| `/session_result` | position, driver_number, number_of_laps, points, dnf, dns, dsq, duration (s), gap_to_leader | `points` returned live though not in the docs page. For qualifying `duration`/`gap_to_leader` are arrays of 3 (docs) |
| `/location`, `/car_data` | date, x/y/z; speed, rpm, throttle, brake, n_gear, drs | about 3.7 Hz, large; not probed |

Probe count: 14 OpenF1 requests (13 successful plus the `year=2022` check).

Timestamps are ISO 8601 UTC with microseconds (`2024-03-02T15:05:20.099000+00:00`).
Join key to Jolpica: `name_acronym` equals Jolpica `code` (VER = VER confirmed for
Verstappen); race result parity: OpenF1 `duration` 5504.742 s and `points` 26.0
match Jolpica `millis` 5504742 and `points` 26.

## 5. Implications for model v2 (spec corrections)

1. Dump exists and is free, but is a normalised relational export (round/session/sessionentry/roundentry/lap), not a copy of the API JSON. `import_history` needs its own CSV mapper, separate from the API mapper. Verify SHA256, reference columns by name. The dump also offers `sql`; CSV stays the right choice (no DB engine lock-in).
2. Spec "Zrzut bazy: CSV, darmowy z opóźnieniem 14 dni" is correct, and add: size 14.5 MB zip, 302 to a pre-signed S3 URL, no schedule, supporter tier needs a key.
3. Qualifying model: dump has Q1/Q2/Q3 as separate sessions and no times on the entry (times are in `lap`). `Session.type` list in the spec (Q, SQ) does not match the dump (Q1-3, SQ1-3, QB/QO/QA). Decide: store one Q/SQ session and merge Q1-Q3 times into `QualifyingResult.q1_ms..q3_ms` in the mapper. Pre-2006 qualifying has one time only (map to q1_ms or add a `single_lap_ms`).
4. `Round`: spec says Jolpica deletes cancelled races from the calendar and sync must flag `is_cancelled`. The dump actually keeps cancelled rounds with `is_cancelled = t` and an empty `number`. Make `Round.round` nullable or skip numberless rounds; the unique (season, round) constraint breaks otherwise. The API behaviour for cancelled rounds is UNVERIFIED.
5. Standings: dump has per-round driver and constructor standings, so the standings backfill is free (no 2,300 API calls). Include `highest_finish`, `is_eligible`, `adjustment_type`: the spec's "do 1978 w konstruktorach", "2007 McLaren" rules map to `is_eligible=f` and `championshipadjustment`. Consider storing `is_eligible`. `podiums` is not provided by either source, so computing it from `Result` (as the spec says) is right.
6. `PointsSystem`: dump has `pointsystem` (24 rows: `driver_position_points` id, fastest-lap points, `is_double_points`, `shared_drive`) and `championshipsystem`. Position points arrays are NOT in the CSVs (only a reference code). Hand-code the per-season tables, or read them from the API (UNVERIFIED).
7. `Result.fastest_lap_rank`: dense only from 2004 (sparse 1958-2003); spec's "2004" is correct for UI purposes. Do not present earlier values as complete.
8. `Result.status`: dump has integer status code plus `detail` text; API has text (`status`). From 2025 all retirements are "Retired". Normalise via text.
9. Practice results: Jolpica has FP1-3 only from 2025 and only in the dump; spec says OpenF1 FP from 2023. Take FP from OpenF1 `session_result`. Spec's `Result.best_lap_ms` for FP should be filled from OpenF1 `duration`.
10. Lap times: spec says 1996 for Jolpica laps. Dump actually contains 731k lap rows (about 1996+) that the spec says not to import. Keep that decision (36 MB CSV, not needed). Qualifying times are the exception: they must be read from `lap`.
11. OpenF1 field names/units differ from the model draft: seconds as floats (`lap_duration`, `duration_sector_N`, `lane_duration`, `stop_duration`), not ms. `RaceControlMessage` needs `scope`, `sector`, `qualifying_phase`. `WeatherSample` adds `pressure`, `wind_direction`. `SessionResult` from OpenF1 carries `points`, `dnf`, `dns`, `dsq`.
12. OpenF1 returns 404 for empty results: client must map to empty, not error. Position/intervals contain pre-session rows (about 1 h before the start); filter by `Session` window if needed.
13. OpenF1 license: spec's "CC BY-NC-SA 4.0" is UNVERIFIED; the docs and README say nothing. Jolpica license is confirmed in TERMS.md. Ask the OpenF1 maintainers or check their LICENSE file before launch. Since the site's non-commercial status governs both sources, an ad/commercial model needs Jolpica's written agreement.
14. OpenF1 price (9.90 EUR) and exact limits (3/s, 30/min) are not on the official docs pages. Treat as UNVERIFIED and make the limits configurable. Backfill cost estimate (about 2k requests, 85 min at 24/min) is consistent with 30/min (not re-verified).
15. Jolpica API: the standings endpoint needs a year; ids are strings; all numbers are strings; optional keys are omitted; responses are cached 10 min by Cloudflare, which matters for the "results every 1 h" job (fine).
16. `Circuit`: API has lat/long as strings, no timezone/country code/length; the dump adds `altitude` and `country_code`. Timezone computed via timezonefinder is still needed.
17. `Driver.headshot_url` and `team_colour` come only from OpenF1 `/drivers` (per session, 2023+); Jolpica has none (dump `team.primary_color` coverage UNVERIFIED).
