# Live data capture

This release captures provider evidence only. Prediction formulas, published
prices used for settlement, frontend behavior and model flags are unchanged.
No Bayesian or Bradley-Terry candidate is installed or activated.

Migration `a9b2e4d7c031 -> b0c3f5e8d142` adds four nullable integer columns to
`odds`: `spread_home_price`, `spread_away_price`, `total_over_price`, and
`total_under_price`. Historical missing prices remain null. Downgrade drops
these columns and loses captured paired prices; it is not an automatic rollback.

Both live odds import paths capture actual American prices. Spread prices are
paired only for complementary home/away lines; totals require matching Over and
Under lines. Missing, invalid or ambiguous paired prices remain null. Existing
line and moneyline extraction is preserved. Imports lock the game row and compare
all lines and prices with the latest snapshot for that game/book. Identical
quotes reuse that snapshot; changes, including price-only changes and reversions,
append new snapshots without modifying old rows.
The upcoming-game importer records per-sport/provider rejection counters for
missing markets, unavailable outcome pairs, line mismatches, invalid or missing
prices, and successfully captured pairs. These counters are emitted in the
worker's source summary; they do not alter odds or selection behavior.

Game imports match exact team names within the requested sport. Explicit
boolean `neutral_site`/`neutralSite` values and non-empty provider venue fields
are retained. Missing or malformed site values remain unknown; home advantage
is not inferred. `python -m scripts.report_odds_capture_coverage` prints a
read-only snapshot, team-identity, venue, and site-status inventory by sport.

Live completed events with valid nonnegative integer scores append an
`odds_api` GameResultObservation with the actual UTC response receipt time.
Valid timezone-qualified provider `last_update` is stored separately as
`source_updated_at`; it never sets `observed_at`. The game-row lock serializes
observation checks with score/status updates, and both commit together.
Repeated unchanged finals do not append; corrections and reversions do.
Historical CFBD observation policy is outside this change.

Existing settlement still runs after score capture. Previously settled picks
are not automatically regraded when scores change.

Deployment requires the exact reviewed source commit, target backend image,
retained rollback images, and a fresh protected backup. This collection-only
change uses existing odds and game columns and requires no migration. Recreate
only backend and upcoming-game-worker, which execute these import paths.
Frontend, database, Caddy, and final-score-worker must remain unchanged. Never
automatically restore the database or downgrade on failure.

Monitor newly inserted paired-price snapshots and live observations by sport,
using snapshot `created_at` and observation `observed_at` from the cutover onward.
No historical availability, prediction improvement or profitable edge is
established by collecting these inputs. Candidate activation remains a separate
decision requiring usable historical evaluation segments and passing criteria.
