# Production Observability

## Phase 1A.1: isolated telemetry storage

This phase supplies storage primitives only. It does **not** instrument workers,
mount operational API routes, add a frontend page, schedule cleanup, send alerts,
or change public health/readiness contracts. No evidence is fabricated or
backfilled: initial operational status remains **unknown**.

Phase 1A.2 adds the opt-in worker instrumentation described below. Phase 1A.3
(admin-protected read API and status evaluation) remains pending.

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
Instrumentation calls storage outside business sessions, after their existing
commit/rollback and close paths. The telemetry pool is process-local; process exit
releases its connections.

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

Disabled telemetry performs zero database work. These settings are not wired
into production Compose. Enabling the flag in a worker process opts into
instrumentation; the additive migration must already exist. This change does not
enable telemetry or apply migrations.

Before worker rollout, validate the actual production image (Python 3.12), not
only a newer developer interpreter. The runtime smoke test imports all telemetry
and worker modules in fresh interpreters and exercises each disabled worker's
startup, polling pass and original exit using mocked business dependencies.
It does not contact providers or a database. Tests are excluded from the image,
so mount the test file read-only:

```sh
docker run --rm --network none \
  -e REQUIRE_PRODUCTION_PYTHON312=1 \
  -v "$PWD/backend/tests/test_worker_production_runtime.py:/app/tests/test_worker_production_runtime.py:ro" \
  --entrypoint python golden-key-backend:production \
  /app/tests/test_worker_production_runtime.py -v
```

Incomplete runtime-evaluated `typing.Generator` annotations can prevent imports
on Python 3.12 even when telemetry is disabled. Generator return annotations
must include yield, send and return types.

## Phase 1A.2: best-effort worker instrumentation

The shared worker adapter registers one UUID per `run_forever` process and one
cycle per complete configured-sport polling pass. Direct `run_once` invocations
use a short-lived instance. Expected competition identities come from the existing
sport mapping. NBA regular and preseason remain separate sources, both internal
sport `NBA`, with leagues `NBA` and `NBA_PRESEASON`.

Disabled mode creates neither a telemetry engine nor a session, wraps no provider
calls, and uses the original settlement service. Enabled mode buffers source
observations in memory during business work. Storage operations occur before
business sessions open or after each sport session closes. Neither worker changes
provider arguments, result dictionaries, calculations, commit/rollback calls,
existing logs, sport continuation, NCAAF shadow hooks, retries or polling sleeps.
If the original session close fails, the adapter suppresses storage and preserves
that original exception rather than running cleanup beside a possibly open
business transaction.

### Boundaries and measured evidence

- **Upcoming:** source start is the existing odds fetch boundary. Final counters
  come from the existing import summaries after import/prediction processing.
  Source finish follows sport-session close; source duration includes intervening
  work on the other competitions of that sport. `prediction_rows_returned`
  counts returned rows, **not** newly created publications: refreshes may reuse
  all predictions. `publications_skipped` counts the existing no-complete-odds
  prediction skips. Created/reused/failed publication counts and created
  prediction-row counts remain NULL because this worker does not receive them.
- **Final-score:** a worker-local observer delegates each existing `_sync_source`
  call exactly once to the unchanged service. Returned source summaries supply
  fetched, matched, finalized, already-final, unmatched, not-final and error
  counts. `games_settled` counts games with a successful settlement, **not**
  settled predictions. `prediction_results_created` and game-date bounds remain
  NULL because source summaries do not expose them.
- Upcoming game-date bounds are normalized from the existing UTC import summaries.
  `last_game_processed_at` is a worker observation: upcoming records successful
  per-game analysis completion; final-score records receipt of a source summary
  containing finalized/already-final games. It is not a provider event timestamp.
  Latest odds/publication timestamps remain NULL: no extra business query or
  provider call reconstructs unavailable timestamps.
- Zero counters are persisted only when execution measured zero. A failed fetch
  retains unknown fetched/processed/prediction counts as NULL. Errors and their
  first allowlisted code are retained. No-games responses alone are successful.
  Fully observed mixed-source outcomes produce partial/failed cycles with
  `telemetry_complete=true`; missing/interrupted coverage is incomplete. NCAAF
  shadow failures increment `auxiliary_errors` without changing business results.

### Heartbeat, recovery and shutdown

Heartbeat and main-loop progress are updated at cycle start, after each closed
sport session, and cycle completion. There is no background heartbeat thread and
no new sleep or signal handler. `heartbeat_seconds` records the poll interval,
not a guaranteed timer cadence. Upcoming remains after-completion scheduling;
final-score remains start-to-start scheduling. Long in-flight operations can
therefore appear stale; heartbeat alone does not prove a worker is healthy.

Before PostgreSQL instance registration, the adapter acquires a non-blocking
session advisory lock on a dedicated telemetry-owned connection. It retains that
connection for its lifetime, separate from both business sessions and the
single-connection telemetry transaction pool. The signed 64-bit key is derived
from a namespaced BLAKE2 digest of the instance UUID, not Python's randomized
hash. Keys and process metadata are not logged. A negligible hash collision
fails closed: it can suppress registration/recovery, not allow unsafe abandonment.

After registration, recovery examines at most 32 old running cycles of the same
worker, oldest first, using telemetry tables only. Per-instance stale cutoff uses
twice its poll interval plus startup grace and its last successful measured
duration, when known. Recent heartbeat **or** progress protects an instance.
For each candidate, the telemetry service non-blockingly acquires
`pg_try_advisory_xact_lock` using the exact same ownership key as the process's
session lock. Proof acquisition, stale-state recheck, lifecycle row locks,
chronology validation and abandonment writes share one telemetry-owned transaction
and physical PostgreSQL connection. A healthy session owner blocks recovery
regardless of old persisted freshness. Connection loss before commit rolls back
recovery; commit or rollback automatically releases its transaction lock.
Competing recoverers cannot hold the same target lock simultaneously;
terminal-state checks prevent repeated transitions afterward. Ordinary explicit
Phase 1A.1 abandonment remains compatible; automatic worker recovery always
requires transactional ownership proof.

Stale timestamps alone never prove a worker is dead. Unsupported databases
(including production SQLite use) disable automatic cross-instance abandonment.
Portable tests use an explicitly injected fake ownership provider; PostgreSQL
tests use actual independent connections and advisory locks. Unavailable ownership
checks degrade telemetry without preventing business startup. No completed cycle
is abandoned. There is no background heartbeat or business-session concurrency.

At safe storage boundaries the adapter verifies its owning connection still holds
the lock; it does not silently reconnect/reacquire a lost lease. Detected connection
loss degrades telemetry and discards ownership resources. Business execution
continues unchanged. Loss cannot be detected continuously during business work;
termination of the ownership connection releases the lock in PostgreSQL and
permits stale-cycle recovery even if the Python process itself remains alive.
Ownership proves the retained telemetry session, not an OS-level process identity.

Python unwinding (including KeyboardInterrupt and SystemExit) establishes one
three-second monotonic deadline in the worker's inner finally block, before the
first interruption-time source flush. Close failures establish it before rethrow.
Source updates, cycle finalization, stopped-state attempts and ownership release
share that deadline; outer layers never extend/reset it. Ordinary cycle completion
does not start an interruption deadline.
The outer process lifecycle also protects acquisition, registration and startup
recovery. Partial acquisition discards its connection on every exception.
Startup unwind establishes the same deadline before cleanup and does not record
an incompletely started process as gracefully stopped. Cleanup failures do not
replace the original startup interruption. Ownership IDs accept UUID objects
or canonical UUID strings; malformed/unsupported IDs raise sanitized
`invalid_input` before engine connection acquisition or SQL.

Interrupted coverage is not marked successful. Unknown/missing source durations
stay NULL. Once the deadline expires, no further telemetry SQL is started and
cleanup may remain incomplete. The retained connection is invalidated/closed
without an unlock query or network rollback; server connection termination
releases its session lock. If time remains, graceful cleanup explicitly unlocks
before discarding the connection. Ownership uses a non-pooled connection, so no
held session lock can be returned to a transaction pool. Buffered evidence can
remain only in memory when cleanup is skipped.

An already-started operation remains subject to configured storage timeouts.
Local connection termination is still attempted when the deadline is exhausted.
This is not a strict three-second wall-clock shutdown guarantee.
Default SIGTERM/abrupt termination is unchanged and does not fabricate shutdown.
Already persisted sources survive; buffered in-flight observations can be lost.
Later startup recovery can mark the stale cycle abandoned.

Only sanitized `TelemetryError` is absorbed at storage boundaries. One fixed
warning per adapter announces unavailable telemetry, then all further storage
work becomes a no-op. Missing tables, timeouts, lock/pool failures and invalid
telemetry configuration cannot replace a business outcome or trigger a business
retry. Failure does not attempt another write just to increment
`telemetry_failures`: missing evidence and the bounded warning indicate degradation.
Business exceptions keep their original propagation/traceback behavior; existing
application error logs are unchanged. No raw payload, exception, URL, host, PID,
credential or customer data is persisted.

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
