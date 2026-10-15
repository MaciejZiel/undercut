# Event catalog

Events go through the transactional outbox (`apps.events`). Payloads are thin: identifiers and a
version, never copies of data. Delivery is at-least-once, so every handler must be idempotent
("recompute for this session"), never "apply this delta". Order is guaranteed per `key` only.

| Event | key | Payload | Published by | Handled by |
|---|---|---|---|---|
| `CalendarSyncDue` | `calendar-sync` | `slot` | scheduler | ingestion |
| `ResultsCorrectionsDue` | `results-corrections` | `slot` | scheduler | ingestion |
| `DemoResetDue` | `demo-reset` | `slot` | scheduler | accounts |
| `HistoryImported` | `history` | `sync_run_id` | ingestion | standings, web cache |
| `SessionResultsFinalized` | `session:<id>` | `session_id`, `version` | ingestion | standings, predictions, notifications, web cache |
| `StandingsUpdated` | `season:<year>` | `season_id`, `after_round` | standings | web cache |
| `PredictionsClosed` | `round:<id>` | `round_id` | scheduler | predictions |
| `PredictionsScored` | `round:<id>` | `round_id` | predictions | notifications, web cache |
| `AnalyticsImported` | `session:<id>` | `session_id` | ingestion | web cache |

"web cache" = a handler that asks the Next.js frontend to revalidate tagged pages.
