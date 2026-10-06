# Production Observability

## Phase 1A.1: isolated telemetry storage

This phase supplies storage primitives only. It does **not** instrument workers,
mount operational API routes, add a frontend page, schedule cleanup, send alerts,
or change public health/readiness contracts. No evidence is fabricated or
backfilled: initial operational status remains **unknown**.

Phase 1A.2 (worker lifecycle/source instrumentation) and Phase 1A.3
(admin-protected read API and status evaluation) remain pending.

### Storage and safe inputs

- `worker_instances`: one application-generated UUID per process start;
  heartbeat and main-loop progress are distinct. Multiple instances of the
  same worker remain visible.
- `worker_cycles`: UUID cycle identity, increasing per-instance sequence, one
  running cycle per instance, explicit terminal outcomes and evidence coverage.
- `worker_cycle_sources`: expected source identity and nullable counters;
  NULL means unavailable/not applicable, while zero is measured zero.

New timestamps use PostgreSQL `TIMESTAMPTZ` with UTC sessions. Callers must
supply timezone-aware timestamps and monotonic durations in milliseconds.
Normal terminal cycle/source `duration_ms` values are caller-measured monotonic
durations, including measured zero. Abandoned cycles store NULL duration: no
wall-clock age is presented as a measurement. Automatically missing sources also
store NULL, not zero; explicitly missing sources may supply a measured duration.
Normal source finish times cannot precede source/cycle start; normal cycle finish
times cannot precede cycle start or recorded source start/finish times.
For a stale running cycle, abandonment is validated under lifecycle locks before
any writes: it cannot precede the maximum of cycle start, instance heartbeat and
main-loop progress, and every source start, finish, last-game-processed,
latest-odds-observed and latest-prediction-published timestamp. Equality is valid.
NULL timestamps contribute no evidence. Game-date bounds describe scheduled
events, not worker activity, and are excluded from this chronology boundary.
Rejected abandonment leaves cycle, sources and instance unchanged; a later valid
request can succeed. Completed cycles remain protected by the terminal-state check.
SQLite is supported for portable unit tests, not PostgreSQL concurrency proof.

The storage service accepts only UUIDs, validated source identifiers, UTC
timestamps, bounded counters and allowlisted error codes. It never accepts
business ORM objects, sessions, arbitrary payloads or exception messages.
Do not store credentials, auth data, raw provider responses, stack traces, SQL,
database URLs, filesystem paths or customer information.

Safe error codes: `provider_unavailable`, `invalid_source_data`,
`publication_failed`, `settlement_failed`, `auxiliary_failed`, `worker_stopped`,
`cycle_abandoned`, `telemetry_incomplete`.

### Transactions and state transitions

The lazy telemetry engine is separate from the business engine/session.
Each operation owns a short explicit transaction, with pool size 1, overflow 0,
pool acquisition timeout 0.2 seconds, connect timeout 2 seconds, statement timeout
500 ms and lock timeout 100 ms. There are no automatic retries. Only the owned
telemetry transaction is committed/rolled back. Errors use sanitized
`TelemetryError` codes; callers must treat missing evidence as unknown.

Isolation prevents telemetry transaction failure from altering caller-owned
business work; it does not eliminate contention for shared PostgreSQL resources.
Later instrumentation must call the recorder outside business locks and after
successful business commits. Dispose the engine on process shutdown.

All lifecycle operations serialize on the owning instance before cycle/source
updates. Cycle identity and source identity support exact idempotent retries.
Conflicting retries are rejected; terminal outcomes cannot be rewritten.
Omitted counters and error codes preserve existing evidence. Explicit cumulative
counter decreases or clearing/replacing a recorded error code are conflicts,
including at finalization. Sources with recorded errors, failed publications or
an error code cannot succeed; use partial/failed and retain the evidence.
While a source is mutable, delayed timestamp observations are accepted and merged:
latest/progress fields retain the maximum, game-date minimum retains the minimum,
and game-date maximum retains the maximum. Instance heartbeat/progress uses the
same maximum rule. Older/equal observations that change nothing return false.
Known timestamps cannot be explicitly cleared. Terminal retries must match the
stored aggregate evidence and outcome; conflicting terminal changes are rejected.
Expected sources must match the registered manifest.
Failure-count increments require the caller's expected previous count, so an
exact retry returns the same increment rather than double-counting it.

Sources transition pending -> running -> succeeded/partial/failed, or
pending/running -> missing. Failed/partial cycles finalize unfinished source rows
as missing. Success requires complete expected source coverage and no recorded
errors. Abandonment locks and rechecks heartbeat, main-loop progress and running
state before writing abandoned evidence; it never overwrites a completed cycle.
Stopped instances cannot begin work or receive heartbeat/progress updates.

### Settings

| Variable | Default | Bounds |
|---|---:|---|
| `OPERATIONS_TELEMETRY_ENABLED` | false | boolean |
| `OPERATIONS_CYCLE_RETENTION_DAYS` | 30 | 1..365 |
| `OPERATIONS_STARTUP_GRACE_SECONDS` | 120 | 15..3600 |
| `OPERATIONS_TELEMETRY_STATEMENT_TIMEOUT_MS` | 500 | 50..5000 |
| `OPERATIONS_TELEMETRY_LOCK_TIMEOUT_MS` | 100 | 10..1000 |
| `OPERATIONS_TELEMETRY_POOL_TIMEOUT_SECONDS` | 0.2 | finite, 0.01..2 |
| `OPERATIONS_TELEMETRY_CONNECT_TIMEOUT_SECONDS` | 2 | 1..10 |

Disabled telemetry performs zero database work. These settings are not yet wired
into production Compose; enabling storage does not instrument existing workers.
Startup grace is reserved for later status evaluation.

### Retention and explicit cleanup

From the backend working directory:

```powershell
.\.venv\Scripts\python.exe -m scripts.prune_worker_telemetry --dry-run
.\.venv\Scripts\python.exe -m scripts.prune_worker_telemetry --batch-size 500
```

Each invocation deletes at most 500 history rows (cycles plus retired instances,
with source rows cascading). A PostgreSQL transaction-level advisory lock excludes
overlapping cleanup. Dry-run takes the same lock but changes no records.
Output is a deterministic bounded JSON summary. Storage failure exits 1;
cleanup-lock contention exits 2. Disabled mode reports `enabled: false`
without connecting. Nothing is scheduled by this phase.

Terminal cycles older than the retention cutoff are eligible, with cascading
source deletion. The newest cycle for a nonretired instance is retained as its
sequence anchor, even beyond the retention period, preventing sequence reuse.
Stopped/abandoned instances retire only after their stop, heartbeat and progress
timestamps are older than the cutoff and all cycle history has been removed.
Running cycles and fresh/running instances are never deleted. Exact-cutoff
timestamps are retained. Repeat bounded invocations to drain a backlog.

### Migration and rollback

Migration `e7b4c2d9a610`, parent `c8d2f6a109b4`, adds only the three telemetry
tables with named checks, indexes, unique keys and cascading telemetry FKs.
No existing business table/constraint changes and no history backfill occur.

Apply an explicit migration only through a separately approved guarded rollout.
Normal code rollback can leave the additive tables in place. Downgrade destroys
telemetry history: stop telemetry writers and export records first. Downgrade
drops sources, cycles, then instances; it does not roll back business data.

### Validation

Portable tests cover disabled/lazy behavior, storage transitions, constraints,
idempotent retries, retention, CLI results and transaction isolation.
PostgreSQL tests require `METRIC_TEST_POSTGRES_URL` pointing to localhost and
database `metric_integrity_test`. They use disposable per-test schemas, block
HTTP, and verify real constraints, concurrency, advisory locks, timeouts,
timezone behavior and upgrade/downgrade/upgrade without business-schema changes.
