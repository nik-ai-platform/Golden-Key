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
The upcoming-game worker also logs per-market capture counts, separating missing
markets, ambiguous outcomes, line mismatches, invalid/missing prices, and captured
pairs. These counts are collected from each provider response and do not fill or
rewrite historical snapshots.

Game imports scope exact team-name lookup to the requested sport. They retain
neutral-site and venue metadata only when the source supplies explicit values;
unknown neutral-site status remains unknown and is not treated as a home game.

Live completed events with valid nonnegative integer scores append an
`odds_api` GameResultObservation with the actual UTC response receipt time.
Valid timezone-qualified provider `last_update` is stored separately as
`source_updated_at`; it never sets `observed_at`. The game-row lock serializes
observation checks with score/status updates, and both commit together.
Repeated unchanged finals do not append; corrections and reversions do.
Historical CFBD observation policy is outside this change.

The read-only team-scoring validator reports candidate-margin rejections by
sport and chronological evaluation period, separates margin availability from
cover-probability calibration availability, compares candidate and baselines on
the same forecastable games, and summarizes frozen-price coverage by daily
vintage and since the first captured paired quote per sport. Its observation
inventory distinguishes valid known-site and unknown-site final receipts and
checks provider identity coverage against the team IDs used by observed games.
It uses no source update time or kickoff as a substitute for a receipt timestamp.

Existing settlement still runs after score capture. Previously settled picks
are not automatically regraded when scores change.

Deployment requires the exact reviewed source commit, target backend image,
retained rollback images, and a fresh protected backup after stopping backend
and both application workers. Verify archive listing and checksum, apply the
migration using the target image, then recreate only those three services.
Frontend, database and Caddy must remain unchanged. Never automatically restore
the database or downgrade on failure.

Monitor newly inserted paired-price snapshots and live observations by sport,
using snapshot `created_at` and observation `observed_at` from the cutover onward.
No historical availability, prediction improvement or profitable edge is
established by collecting these inputs. Candidate activation remains a separate
decision requiring usable historical evaluation segments and passing criteria.
