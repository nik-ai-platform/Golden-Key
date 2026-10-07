# Backend

Backend services and API layer for the nik-ai-platform.

See [Production Observability](../docs/PRODUCTION_OBSERVABILITY.md) for the
isolated Phase 1A.1 storage foundation and opt-in Phase 1A.2 worker instrumentation.
Instrumentation is not deployed or enabled and remains disabled by default.
Dedicated PostgreSQL session locks protect process ownership; recovery uses a
transaction-level advisory lock on the same key and physical connection as its
abandonment transaction. Connection loss before commit rolls back recovery.
Unsupported ownership checks disable cross-instance abandonment. Startup unwind
and shutdown use one shared cleanup budget. Invalid ownership IDs fail before
resource acquisition. Loss of the running ownership session can permit recovery
before Python notices, without affecting business work. No operational API or
frontend is included.

## Structure

- `api/` - API endpoints and handlers
- `services/` - Business logic
- `models/` - Data models
- `migrations/` - Database migrations
- `tests/` - Test suite
- `config/` - Configuration files

## NBA competition ingestion

The upcoming-game and final-score workers poll the NBA sources independently:
`basketball_nba` stores `sport=NBA, league=NBA`; `basketball_nba_preseason`
stores `sport=NBA, league=NBA_PRESEASON`. Provider event IDs are the sole game
identity; no calendar inference, fuzzy matching, or migration is used.
A conflicting competition marker is logged and rejected rather than overwritten.
One unavailable NBA source does not stop the other source. If both fail, the
import raises a sanitized error. Single-source sports retain failure propagation.

Upcoming-worker competition summaries include fetched/processed games, created
and refreshed games, games with usable odds, games without usable odds,
returned predictions, prediction skips/errors, and the imported UTC date range.
The existing `imported` total includes refreshes; prediction counts include
reused predictions and are not insertion counts. Score summaries are also
logged per provider source. Provider request errors log their type, not
credential-bearing exception URLs.

Prediction refresh uses immutable revisions, not an identical-price-only reuse
rule. A complete current publication is reused only when its full input
fingerprint matches: effective sport/runtime version, all selected odds
values/sportsbook, resolved NPI factors/weights/explanations, total baseline, and
simulation settings. A changed input (including same-version profile changes)
appends three new predictions with the selected snapshot's provenance. Unchanged
inputs may reuse the original frozen snapshot; new snapshots are still stored.
Legacy rows marked `unverified:legacy` are preserved and regenerated once if eligible.
Saved picks remain attached to their original immutable prediction, but do not
freeze future publications. Started/final/settled games remain frozen.
Odds snapshots remain append-only with unchanged retention.
Future preseason games appear in NBA upcoming/daily-card feeds; already-started
games remain excluded. The provider odds feed only supplies bookmaker-listed
events, not a complete preseason schedule.

Default Performance, Performance Intelligence (including historical model,
range, and calibration reports), and performance analytics exclude
`league=NBA_PRESEASON` at their game-history query boundaries. Preseason
predictions, saved picks, finals, and settlements remain stored. No API contract
or frontend change is made, so customer cards do not display a preseason badge.
Season continues to use the existing calendar-year convention, not a new
cross-year NBA season definition.

Model factors, snapshot-based analytics/replay, training datasets, and
game-linked backtest reports/promotion evaluations exclude preseason before
limiting or aggregating. Explicit per-game history remains accessible.
The legacy `BacktestService.create_result` writer reselects verified regular-season
evaluations before creating a summary; existing provenance-free backtest summary
rows are retained but excluded from default reports. These rows cannot establish
their original phase mix, and newly written summaries still lack durable game
lineage, so default reporting uses game-linked results instead.

No in-application persistent writer for `ModelPerformance` was found. Existing
rows cannot prove phase isolation. Default model metrics/list/comparison and
dashboard model summaries are instead derived from regular-season game-linked
outcomes, leaving stored aggregate records unchanged. Models represented only
by provenance-free aggregates no longer appear in these default data-driven
reports. No historical aggregate is relabeled, guessed phase-clean, or deleted.
Stored `ModelVersion` performance fields also lack per-game provenance. The
model-factor endpoint derives its displayed accuracy from scoped outcomes and
game-linked backtests rather than trusting historical registry aggregates.
Its headline metrics are scoped to the selected registry model's sport and
version; backtest wins and sample counts are aggregated in SQL without loading
global history. Replay checks phase on the game it has already loaded rather
than issuing an extra per-snapshot query.

## Production metric contract (NPI-5.0)

### Prediction-refresh revision migration

Migration `c8d2f6a109b4` merges both prior heads (`c6f2a8d4e913` and
`a4c8e2f19b73`) into one final head and replaces the former unique
`(game_id, model_version, market)` index with
`(game_id, model_version, market, generation_id)`. It backfills each existing
prediction with a deterministic UUID-shaped identity derived from
`md5('legacy-prediction:' || id)` and the explicit `unverified:legacy` fingerprint
marker. These markers do not claim historically verified model inputs.
Both fields are NOT NULL, checked, internal metadata. New ORM fixture/manual
records without known input provenance use `unverified:manual`; the production
standalone POST writer computes a payload fingerprint and locks the game to
deduplicate sequential/concurrent identical writes. Changed payloads append
revisions, unless the game is started, final, or settled.
Existing prediction
IDs, prices, results, analyses, factors, saved picks, and publication order are
not rewritten or deleted. These internal fields are not added to API schemas.
PostgreSQL upgrade is transactional. Downgrade restores the two parent heads and
original unique index only if no duplicate non-NULL game/model/market keys exist;
otherwise it raises before any DDL and retains all revision history. Re-upgrade
of legacy data produces the same deterministic identities.

Safe deployment order (startup migrations are disabled):

1. Keep upcoming-game-worker stopped and quiesce all other prediction writers.
2. Stop backend and final-score-worker for the maintenance cutover.
3. Deploy the new artifact without starting services.
4. Explicitly run `alembic upgrade head` (or `heads`); verify `alembic current`
   reports only `c8d2f6a109b4`, both parent branches are present, and revision
   constraints/backfill and existing IDs/FKs are intact.
5. Start the updated backend and check readiness, then start final-score-worker.
6. Start upcoming-game-worker last.

The rollback `0fc80bc` processes must not resume writing against this schema:
they omit required revision metadata. New ORM readers must not start before
upgrade because they select the new columns. Treat this as a maintenance
cutover, not an unrestricted mixed-version rollout. No automatic migration or
production service restart is performed by the hotfix.

The writer holds the same PostgreSQL game-row lock as settlement and commits
all three predictions, analyses, factors, and rule-intelligence records together.
Failures roll back the entire publication. Canonical lookup materializes at most
three prediction rows, regardless of stored revision count. Explicit forced
regeneration creates a new revision; reverting inputs never resurrects an older
superseded publication. Changes to calculation implementation must bump the
internal fingerprint contract revision so old outputs are not reused.

The `prediction-refresh-v3` contract hashes effective sport/runtime identity,
sportsbook and all five odds inputs, resolved NPI score and ordered
factors/weights/scores/explanations, the effective total baseline, simulation
default run count/deviation, the moneyline model's class-level deviation, and
analysis version. Factor explanations and order affect published reasoning and
are intentionally retained. The current NPI home-advantage implementation uses
its resolved weight, not raw venue or neutral-site metadata; if an implementation
consumes home context, its resolved factor output participates in the fingerprint.
No prediction/NPI formula is changed.

The contract excludes venue name/city/state, neutral-site/season/league metadata,
database IDs, observation/creation/kickoff timestamps, accuracy/sample statistics,
notes, approvals, reporting fields, and `ModelVersion.changes`. The latter is
descriptive release text: no current calculation consumes it. Effective runtime
version and resolved profile factors, rather than the database row, determine
identity. Numeric normalization is independent of Decimal context, distinguishes
numbers from strings, and mapping ordering is deterministic.

Default performance and factor queries select canonical predictions before
aggregation. Historical version comparisons retain the latest appropriate
publication per game/market/version, not every same-version revision. Current
prediction endpoints select winners in SQL; `/predictions/stored`, saved picks,
results, analyses, corrections, and settlement remain explicitly historical or
exact-ID operations. Settlement retains results for every frozen historical
prediction, while default reports do not count superseded revisions.
The regeneration command refreshes material changes without forcing new
stochastic publications. Re-running the same batch reuses successful identical
publications, including after a partial failure. Each game holds the same row
lock and has an independent transaction; a failed game's publication and
dependent records roll back, while earlier successes remain committed and later
games continue. Output is a deterministic JSON object with `counts` and ordered
`results` for `revised`, `reused`, `protected`, `ineligible`, `no_odds`, and `failed`.
Missing games/non-scheduled games are ineligible; started/final/settled games are
protected. No complete odds is reported explicitly and, like failure, causes a
nonzero CLI exit after the complete summary is printed. Error classification and
fixed safe messages are reported without exposing raw exception text.

Parlays retain original prediction/snapshot provenance. Freshness is established
from the newest non-future observation for the same game/sportsbook only if its
relevant inputs match the frozen snapshot exactly: spread uses both lines and
total; moneyline uses both lines, prices, and total; total uses the posted total.
A newer mismatched/incomplete observation cannot be bypassed by falling back to
an older matching observation. The six-hour check uses that verified observation;
the returned historical snapshot identity/time remains unchanged.

Metric Integrity Phase 1 changes semantics, not NPI weights or score normalization.
`PredictionEngine` generates `NPI-5.0` records. A configured NPI-4.0 or NPI-4.1 runtime
continues to supply its existing sport/version weight profile; generation records
the corrected version. With no configured model, the existing NPI-4.0 profile
lookup/default fallback remains. An explicitly configured NPI-5.0 runtime uses
its own profile when present; missing profiles fall back to in-code defaults
(existing behavior), while invalid profiles raise an error. Other generation versions raise an error rather than claiming
unsupported metric semantics. No registry, profile, or historical rows are
updated by this compatibility mapping.

`simulation_probability` is a nullable 0-100 selected-side estimate: HOME/AWAY
cover probability for spreads, candidate-side win probability for moneylines,
and the selected OVER/UNDER heuristic for totals. New finite generated values are bounded;
missing/nonfinite values are unavailable (nonfinite values are logged).
PASS has no selected-side probability and cannot be an actionable recommendation.
Creation schemas reject out-of-range/nonfinite probability input.

`prediction_metric_contract.selected_side_probability` is the only historical
orientation adapter. It complements verified NPI-4.0/NPI-4.1 AWAY spreads once. NPI-5.0 values,
moneylines, and totals pass through without complementing. Unknown versions or
invalid selections report unavailable with a warning, never a fabricated zero.
Historical out-of-range/nonfinite probabilities are unavailable with a warning,
not clamped into credible estimates. Historical response validation is separate
from strict creation validation, including `/predictions/stored`.
Other malformed/nonfinite historical numeric metrics (NPI, Confidence, edge,
line, odds, and simulation metadata) serialize as null with warnings. Valid
historical values are preserved; no read updates a stored row. Invalid American
odds (nonintegral or absolute value below 100) are unavailable.
Product reads, parlay scoring, and version-separated Performance calibration use
this adapter. Structured probability sentences in historical reasoning are
adapted in response payloads to the same selected-side value (or unavailable);
stored reasoning is not rewritten. Historical Confidence and Risk are returned unchanged. Newly
generated spread Confidence uses selected-side probability with the existing
formula/cap of 95; Risk retains the 80/65 boundaries.

Persisted `projected_edge` remains raw for historical records. `describe_edge`
exposes `selected_side_edge`, `edge_unit`, and `edge_benchmark`: spread/moneyline
use percentage points (spread benchmark 50%, moneyline vig-free implied
probability); totals use scoring points versus the posted total. Legacy AWAY
spread/UNDER signs are adapted on reads; NPI-5.0 stores their selected-pick edge.
Actionable thresholds remain spread >5, moneyline >=3 with positive price-based
expected value in generation, and total >=2. This is not universal expected profit.

The optimizer uses selected-side edge with these market thresholds, preserves
frozen leg identity/prices, and excludes superseded predictions and legs missing
finite probability, Confidence, NPI, edge, or required odds/selection metadata.
Returned average Confidence and `average_model_probability` are numeric means
of valid legs. The latter is not the probability of the combined parlay.
Unclassified aggregate Risk is the string `unavailable`, safe for cached clients.
`average_projected_edge` is deprecated and null because unlike units cannot be
averaged. Use `average_selected_side_edge_by_market` and its explicit units.
The numeric-to-null deprecation is intentional; this repository's old and new
frontends do not render the deprecated edge aggregate. External clients must
honor the deprecation flag and explicit per-market units.
Performance returns separate `npi_4_spread` and `npi_5_spread` reports.

`prediction_publication` chooses one row per game/market by supported semantic
version (NPI-5.0 > NPI-4.1 > NPI-4.0), then highest ID within the version.
Unknown families rank below supported versions and remain unavailable.
Supported market/selection pairs (including PASS) outrank malformed metadata
within the supported-version group before this version ordering; malformed market
identities are not published. Unsupported versions never displace supported ones.
Missing numeric metrics still suppress an older complete pick after supersession.
Selection/availability filtering happens only after supersession, so new PASS
or incomplete rows never resurrect old actionable picks. Slate resolution
advances to a date containing a current actionable pick. Saved picks retain
their exact historical identity. Settlement and audit/version reports may retain
all generations; overall customer counts and breakdowns count only canonical,
non-PASS predictions, even when the canonical row is not yet settled.
Changed odds snapshots append a new corrected generation rather than deleting
the superseded predictions, analyses, or factor results.
Customer reads select canonical IDs with SQL `row_number()` partitioned by
game/normalized market, ordered by exact supported version precedence and ID
descending. Availability filters and limits follow that selection. Historical
generations are not materialized for feeds or overall Performance; independent
version reports deliberately retain historical settlements.
These audit reports stream batches of 200 into summary/calibration counters,
rather than retaining every historical ORM row or Brier sample in memory.

Market/selection parsing has one explicit Python/SQL contract: require a string,
remove ordinary space, tab, carriage return, and newline throughout the token,
then lowercase and accept only `spread`, `moneyline`, `total` or
`home`, `away`, `over`, `under`, `pass`, respectively. Other whitespace, blank
values, aliases, and unsupported tokens are unavailable. Customer selections
are emitted uppercase and markets lowercase; raw historical rows are unchanged.
SQL uses explicit `replace` calls and a whitelist, never default `trim`.
Selection must also be valid for its market; no unknown selection defaults to AWAY.

The shared actionable-completeness predicate requires supported version/selection,
finite NPI, Confidence, selected-side probability and edge, and valid American
odds in all markets. Spreads require HOME/AWAY and a finite line; totals require
OVER/UNDER and a finite line; moneylines require HOME/AWAY but no line. PASS and
incomplete canonical rows are informational only and never resurrect old picks.
Existing market edge thresholds and moneyline price policies remain separate.
The optimizer additionally verifies the frozen odds identity/freshness.

Settlement skips only explicitly ungradeable historical betting data (invalid
selection, missing/nonfinite line, invalid/missing frozen price). It logs and
returns each skipped ID/reason without inventing a result or updating the row.
Existing settlements remain unchanged. Valid rows commit together; unexpected
database/programming failures propagate to the caller for transaction rollback,
not a success-shaped response. Repeated settlement remains idempotent.
On PostgreSQL, settlement locks the Game row with `SELECT ... FOR UPDATE` before
reading results, refreshing the game after acquiring the lock. A competing
same-game transaction waits, then reads committed results and returns no new
settlements. Regrading uses the same lock. The existing result uniqueness
constraint remains defense in depth; unrelated integrity failures are not caught.
The PostgreSQL integration tests are opt-in through `METRIC_TEST_POSTGRES_URL`
and accept only a loopback PostgreSQL database named `metric_integrity_test`.
Use a disposable PostgreSQL instance, never deployment credentials. Each test
creates/drops a uniquely named test schema with only the settlement/read tables;
it does not run application migrations. Tests prove blocking with
`pg_blocking_pids`, not SQLite lock behavior. Without this explicit test URL,
the five PostgreSQL integration cases report skips.

Cross-market ranking uses dimensionless threshold multiples: spread edge / 5,
moneyline edge / 3, total edge / 2, with negative support floored to zero.
Daily-card and parlay edge contributions saturate at two threshold multiples.
This is ranking strength, not probability, expected value, profit, or a universal
edge; it is not displayed as a customer betting metric.
Internal daily ranking scores and parlay scores/components are omitted from
customer JSON. Older cached clients may retain these fields but must not depend
on their presence; the compatible frontend displays Model Probability instead.

No database migration or historical rewrite is required or performed.
An existing valid NPI-4.0 registry/model/profile can generate NPI-5.0 without
creating a new registry entry.

Production rollout must rebuild/recreate `backend`, `upcoming-game-worker`,
`final-score-worker`, and the compatible `frontend` together. Replacing an image
tag does not replace running workers. An old upcoming worker can keep producing
NPI-4.x records; semantic publication ordering prevents those late legacy writes
from superseding corrected records, but coordinated deployment is still required.

### Coordinated rollout and rollback boundary

1. Record exact pre-deployment commit and image identifiers for all four services.
   Take and verify a database backup/recovery point, including a tested recovery
   procedure. A Git backup branch does not protect database state.
2. Stop prediction-writing workers (including any scheduled prediction writers)
   during the transition. Stop settlement workers as well so readers and writers
   do not run incompatible images.
3. Rebuild/recreate `backend`, `frontend`, `upcoming-game-worker`, and
   `final-score-worker` as one coordinated rollout. Verify actual running image
   identifiers before resuming writers; changing an image tag is insufficient.
4. Check worker health/logs, API health, and that newly generated rows say NPI-5.0
   while retaining the configured profile weights. Verify one canonical row per
   game/market, late legacy rows do not supersede corrected rows, and customer
   Performance totals agree with canonical non-PASS settled counts. Inspect
   reported settlement skips; verify unavailable metrics render safely.
   Spot-check an NPI-4.0/NPI-4.1 AWAY spread: customer probability must be
   `100 - stored probability`, once only. An NPI-5.0 AWAY spread must equal its
   stored selected-side probability unchanged. Confirm one published customer bet
   per game/market and zero customer bets for normalized PASS variants (including
   tab/CR/LF and mixed casing). Compare valid canonical final picks to settlements
   so missing settlements are distinguishable from explicitly logged skips.

After NPI-5.0 rows exist, rolling backend/readers back to code lacking canonical
4.x/5.0 publication and serialization is unsupported: it can double customer
Performance totals and misorient probabilities. Safe application rollback must
retain this compatibility layer and coordinate all four services, stopping
writers during the transition and repeating the checks above. Restoring commit
288f05b alone is not a supported rollback.

A full database restore is emergency recovery, not normal application rollback.
It may discard unrelated post-deployment billing, saved-pick, ingestion, and
settlement activity. Use the verified recovery plan and reconcile that activity;
do not blindly restore a database merely to revert application code.

## Setup

1. Copy environment variables:

	```powershell
	Copy-Item .env.example .env
	```

	Required variables: `DATABASE_URL`, `SECRET_KEY`, `JWT_SECRET`, `OPENAI_API_KEY`, `SPORTSBOOK_API_KEYS`, `REDIS_URL`, `SMTP_SETTINGS`.
	Stripe sandbox billing is disabled by default. To enable it locally, set `STRIPE_TEST_MODE_ENABLED=true`, provide an `sk_test_` value through `STRIPE_SECRET_KEY`, set `STRIPE_WEBHOOK_SECRET`, and map the canonical plans to test prices with `STRIPE_PRICE_IDS={"pro_monthly":"price_...","pro_annual":"price_..."}`.
	Apple subscription verification is also disabled by default. Sandbox verification requires `APPLE_SUBSCRIPTIONS_ENABLED=true`, `APPLE_APP_STORE_ENVIRONMENT=sandbox`, the bundle and product IDs, and `APPLE_ROOT_CA_PATHS` as a JSON list of local DER-encoded Apple root CA certificate paths. App Store Connect API credentials remain environment-only and are not needed by these verification-only endpoints.

2. Start PostgreSQL with Docker (host port `5433` -> container `5432`):

	```powershell
	Set-Location ..
	docker compose up -d postgres
	Set-Location backend
	```

3. Install Python dependencies:

	```powershell
	py -m pip install -r requirements.txt
	```

4. Create database tables:

	```powershell
	py -c "from app.database.base import Base; from app.database.session import engine; import app.models; Base.metadata.create_all(bind=engine)"
	```

5. Run the API:

	```powershell
	py -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
	```

6. Verify endpoints:

	- `http://127.0.0.1:8000/openapi.json`
	- `http://127.0.0.1:8000/api/v1/teams/`

## Authorization Matrix

All role-based authorization denials return the same payload:

```json
{
  "detail": "Insufficient permissions"
}
```

| Endpoint | Viewer | Analyst | Admin |
| --- | --- | --- | --- |
| `GET /api/v1/dashboard` | ✅ | ✅ | ✅ |
| `GET /api/v1/predictions/{game_id}` | ❌ | ✅ | ✅ |
| `POST /api/v1/imports/{sport}` | ❌ | ✅ | ✅ |
| `GET /api/v1/backtests/*` (planned) | ❌ | ✅ | ✅ |
| `GET /api/v1/users/*` (planned) | ❌ | ❌ | ✅ |

Notes:

- `backtests` and `users` routes are not implemented yet, but target policy is documented here for frontend planning.
- Any endpoint protected with `require_viewer`, `require_analyst`, or `require_admin` follows the same matrix semantics.

## OpenAPI Authorization Reference

Swagger/OpenAPI auth flow uses OAuth2 bearer with this token URL:

- `POST /api/v1/auth/login`

Dependency guards and role policy mapping:

| Dependency | Allowed Roles | Typical Use |
| --- | --- | --- |
| `require_viewer` | `viewer`, `analyst`, `admin` | Read-only dashboards, analytics, intelligence views |
| `require_analyst` | `analyst`, `admin` | Prediction and import workflows |
| `require_admin` | `admin` | Administrative/management operations |

Example endpoint annotations:

- Router-level guard:

	```python
	router = APIRouter(
			prefix="/imports",
			tags=["Imports"],
			dependencies=[Depends(require_analyst)],
	)
	```

- Endpoint-level guard:

	```python
	@router.get("/{team_id}/intelligence")
	def get_team_intelligence(
			team_id: int,
			_current_user=Depends(require_viewer),
			db: Session = Depends(get_db),
	):
			...
	```

Contract for role-denied requests remains stable:

```json
{
	"detail": "Insufficient permissions"
}
```

## Prediction Contract Note

`GET /api/v1/predictions/{game_id}` is a single-game prediction snapshot endpoint.

- It is not a real-time analytics feed.
- Returned NPI values are model outputs, not live scoreboard data.
- For historical and aggregate analytics, use `/api/v1/analytics/*` endpoints.
