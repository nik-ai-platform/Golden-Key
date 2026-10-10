# Prospective team-scoring scheduler operations

This scheduler operates the frozen `TEAM-SCORING-PROSPECTIVE-1.0` shadow
evaluation. It does not change customer predictions, saved picks, optimizer
ranking, database schema, or candidate activation.

## Installed jobs

- Recorder: hourly at minute 07 UTC; one initial startup run is also scheduled
  30 seconds after timer installation.
- Settlement and daily coverage: 00:47 UTC daily; one initial startup run is
  also scheduled 60 seconds after timer installation.
- CFBD shadow score refresh: Sunday at 03:17 UTC. The initial seed requests
  only the 2025 and 2026 season game lists (two API requests); each weekly
  refresh requests the current season once.

The recording, import, settlement, and coverage units share a nonblocking
`flock` lock. Systemd enforces runtime, memory, CPU, and task limits. Each job
runs in an ephemeral, read-only-root Docker container with dropped Linux
capabilities; only the protected evaluation directory is writable. Failures
produce a nonzero unit result and a journal entry, and the runner appends a
protected run-status record. No secrets are logged.

The evaluator uses a PostgreSQL repeatable-read, read-only transaction. Its
attempts, CFBD score receipts, settlement evidence, daily reports, and
scheduler status are append-only files outside application tables. Hourly
attempt batches are compressed and immutable; a stable run ID prevents retry
duplication. Repeated attempts are retained, but only the earliest eligible
pre-kickoff margin forecast for a unique game is used for headline evaluation.
New score-observation IDs append correction evidence rather than replacing
earlier settlement records.

Run IDs are fixed to their schedule window (UTC hour for recording, UTC date
for evaluation, and ISO week for CFBD refresh), so a retry in the same window
cannot create a duplicate batch or report. The weekly refresh defaults to the
current UTC season; bootstrap imports can explicitly request multiple seasons.

## Provider and history constraints

The configured Odds API feed supplies scheduled event home/away labels, odds,
and recent final scores, but does not provide neutral-site or venue metadata in
the configured event payload. Home/away labels are not used to infer
`neutral_site=false`.

CFBD supplies explicit `neutralSite`, venue, home/away provider team IDs, and
historical scores in the season game response. Shadow history is accepted only
when the site flag is explicitly true or false and both CFBD team IDs resolve
through the existing NCAAF-scoped `TeamProviderIdentity` table. Unmapped teams,
unknown sites, incomplete scores, and non-final events remain visible as
rejection counts.

The existing application historical-import service stores provider-updated or
kickoff-derived timestamps in `observed_at`; those old CFBD rows are therefore
excluded from shadow model inputs. The shadow-only import stores the actual
response-receipt time and keeps the source-updated timestamp separately. This
late receipt can be used only in forecasts generated after that receipt; it
cannot enter earlier predictions. Corrections are appended with a new actual
receipt time. The CFBD key is used only by the weekly shadow importer, which
makes one current-season games request per run; no other provider is polled by
this scheduler.

## Promotion guard

The scheduler never changes the frozen candidate parameters or promotion
criteria, creates customer-facing recommendations, or enables the candidate.
The fixed gates remain in
[`PROSPECTIVE_TEAM_SCORING_EVALUATION.md`](./PROSPECTIVE_TEAM_SCORING_EVALUATION.md).
Coverage reports are descriptive; insufficient history, unknown sites, missing
paired prices, or too few settled games do not cause thresholds to be relaxed.
