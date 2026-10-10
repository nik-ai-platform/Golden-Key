# Prospective team-scoring evaluation

This protocol is frozen before the prospective forecast records are generated.
It is an isolated shadow evaluation; the candidate is not called by customer
prediction APIs, saved-pick flows, or parlay ranking.

## Frozen period and candidate

- Period start: `2026-10-09T23:49:28Z`, after the collection-only deployment and
  its first completed collection cycle.
- Collection-only production commit: `a9a6b105fa0910adcabcde0212bbaf1e7ca24efd`.
- Candidate: `TEAM-SCORING-RIDGE-1.0`, source commit
  `a7707f2726315d56d00fb55c5ea7533e7e18681e`, scorer blob
  `486452a5ab43438a0d8d06c1691280110a939d61`.
- Fixed candidate parameters: ridge penalty `20.0`, at least 8 prior games
  overall, at least 3 prior appearances per target team, and at least 30 earlier
  settled forecast errors before emitting cover probabilities.
- The scorer remains disabled (`ACTIVATION_ENABLED = False`). No parameter,
  feature, or threshold tuning is allowed using this period.

## Timestamp and record rules

The one-off recorder reads score observations and frozen odds only. It writes
append-only JSON Lines to a protected evaluation file, never to predictions,
prediction results, user picks, or optimizer tables. Each attempt records the
candidate version, prediction timestamp, target game and teams, neutral-site
and venue values, each contributing score observation's ID, scores, teams,
kickoff, site, and actual `observed_at` receipt,
frozen odds snapshot ID/time, both signed spread lines, actual prices, forecast
margin if available, and explicit rejection reasons.

Only score observations with a valid final status, valid scores, kickoff before
the attempt, and actual receipt timestamp strictly earlier than the attempt may
enter the candidate history. Provider source update times, game dates, and
import times are not substitutes for receipt time. Odds snapshots must have
been stored before the attempt. Unknown venue status is rejected; it is never
interpreted as a non-neutral home game. Historical records and the snapshot
inputs are not updated or backdated.

Every collection-cycle invocation may append a new attempt. For evaluation,
use only the earliest available pre-kickoff candidate forecast per unique game;
retain later attempts and all rejection records for audit, but do not count them
as additional samples. Candidate cover probabilities use only prior unique
candidate-forecast games whose valid final score receipts were available before
the new forecast timestamp. A missing or unpaired price never becomes an
imputed price.

## Evaluation and promotion gates

Report results separately by sport. Candidate margin MAE/RMSE and cover metrics
must be paired on exactly the same games as the relevant baseline. The market
margin baseline is the frozen implied home margin (`-spread_home`); report the
incumbent NPI-derived margin only as a separate comparison. Grade cover from
actual final scores plus the frozen selected-side line exactly once. Whole-point
pushes remain a separate outcome and are excluded from win-rate denominators.

No promotion recommendation is allowed unless each sport has at least 200
unique eligible prospective games spanning a complete competition season.
Candidate margin MAE must beat the frozen market-margin baseline with a
game-level paired 95% bootstrap confidence interval wholly below zero for
candidate-minus-baseline error. Cover-probability promotion additionally
requires at least 200 scored non-push games, at least 30 earlier unique errors
at each probability timestamp, paired de-vigged-market Brier improvement whose
95% confidence interval is wholly below zero, and no log-loss degradation.
Report calibration intercept/slope and uncertainty; do not substitute confidence
ratings for probabilities.

Report unit-stake ROI only for candidate selections made at the recorded actual
prices and the frozen positive-expected-value rule. Missing prices are excluded
and counted. An activation proposal additionally requires at least 200 settled
priced candidate selections and a game-level 95% ROI confidence interval with a
lower bound above zero. Even if all statistical gates pass, activation requires
a separate review and explicit approval; this protocol does not enable the
candidate.

## Running and interpreting the recorder

Run the recorder as an isolated, read-only one-off after a completed collection
cycle, mounting the protected output file separately. Serialize invocations so
two runs cannot append duplicate records concurrently. PostgreSQL is read from a
repeatable-read, read-only transaction; the output directory and JSONL file are
restricted to owner access. The runner refuses to execute before the frozen
period start. It does not create a production service or migration. A run with
zero available candidate margins or probabilities is a valid coverage result;
it is not a customer-facing fallback or a reason to relax the frozen gates.
