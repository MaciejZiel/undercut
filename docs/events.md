# Event catalog

Events go through the transactional outbox (`apps.events`). Payloads are thin: identifiers and a
version, never copies of data. Delivery is at-least-once, so every handler must be idempotent
("recompute for this session"), never "apply this delta". Order is guaranteed per `key` only.

| Event | key | Payload | Published by | Handled by |
|---|---|---|---|---|
| `CalendarSyncDue` | `calendar-sync` | `slot` | scheduler | ingestion |
| `ResultsCorrectionsDue` | `results-corrections` | `slot` | scheduler | ingestion |
| `PracticeResultsDue` | `session:<id>` | `session_id` | scheduler | ingestion (OpenF1 `session_result`: practice classification, hourly for 12 h after a practice session ends) |
| `SessionResultsDue` | `session:<id>` | `session_id` | scheduler | ingestion (Jolpica results, then standings; hourly after the session ends until the results are final, then a daily catch-up) |
| `AnalyticsDue` | `session:<id>` | `session_id` | scheduler | ingestion (OpenF1 laps, stints, pit stops, positions; every two hours in the first day after a race or sprint) |
| `DemoResetDue` | `demo-reset` | `slot` | scheduler | accounts |
| `WeeklyHealthMailDue` | `weekly-health-mail` | `slot` | scheduler | ops (mails `ALERT_EMAIL_TO` the pipeline state; keeps the SMTP key in use) |
| `HistoryImported` | `history` | `sync_run_id` | ingestion | standings, web cache |
| `SessionResultsFinalized` | `session:<id>` | `session_id`, `version` | ingestion | standings, predictions, notifications, web cache |
| `StandingsUpdated` | `season:<year>` | `season_id`, `after_round` | standings | web cache |
| `PredictionsClosed` | `round:<id>` | `round_id` | scheduler | predictions |
| `PredictionsScored` | `round:<id>` | `round_id` | predictions | notifications, web cache |
| `UserDeleted` | `user:<id>` | `user_id` | accounts | predictions (anonymise / clean up what the user owned) |
| `AnalyticsImported` | `session:<id>` | `session_id` | ingestion | web cache |
| `RaceResultEmailRetry` | `round:<id>` | `round_id`, `attempt` | notifications | notifications (re-sends only what the `SentEmail` markers show as missing: 5, 10, 20, 40 and 80 minutes) |

"web cache" = a handler that asks the Next.js frontend to revalidate tagged pages.

`UserDeleted` is published in the same transaction that deletes the account. The user row is already
gone when handlers run, so they only get the id: they must be idempotent and must not look the user
up. Rows with a database-level cascade are removed by the deletion itself; the event exists for data
that must outlive the user in anonymised form (e.g. predictions kept in rankings as "Deleted user").
