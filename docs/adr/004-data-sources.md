# ADR 004: Data sources, licences and import strategy

Status: accepted

## Decision
- **Jolpica-F1** for history (free CSV dump, no login) and for current results (API).
- **OpenF1** for 2023+ analytics.
- Both are non-commercial community projects: Undercut is non-profit, shows no ads or payments,
  credits both sources in the footer and on a sources page, and does not use official logos or
  driver photos.
- The Jolpica terms are CC BY-NC-SA 4.0; the OpenF1 repository states no licence on its docs
  page, so it is treated as non-commercial and attributed the same way.
- Standings are imported as published. Results keep the constructor on race day.

## Consequences
- The importer is idempotent and rows edited by hand (`manual_override`) are never overwritten.
- The API client stays at 80% of the published limits and identifies itself.
- A shared database dump of derived data would need the same licence.
