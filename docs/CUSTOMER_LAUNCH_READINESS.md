# Free Preview and Premium launch

This batch is local implementation and validation, not authorization to deploy,
enable live billing, send mail, or alter customer data. Legal pages are
plain-language operational drafts requiring attorney review.

## Access policy

| Audience | Available experience |
| --- | --- |
| Public | Product information, How It Works, metric education, sign-up/sign-in/recovery, legal drafts and support |
| Free signed-in account | Safe dashboard/slate preview, profile, subscription/billing and education |
| Active canonical Premium | Full selections/odds, game analysis, saved picks, parlays and performance intelligence |
| Admin | Explicit authorized administrative access; existing role checks remain in force |

`require_premium_user` is the authoritative customer API dependency. It delegates
to the canonical `premium` application entitlement, checks its validity window,
and explicitly preserves admin access. A legacy subscription plan string,
frontend badge, URL parameter, or successful checkout redirect never grants
access. A canceled/past-due/expired provider does not grant entitlement. An active
subscription scheduled for cancellation retains its current-period entitlement
until cancellation or expiry.

The authenticated `/api/v1/product/preview` response is an explicit allowlist of
game identity, teams, competition, start time and lifecycle state. It queries
games only, returns at most 100 rows across a seven-day slate, and contains no
selections, odds, ranking, model confidence, probabilities or premium analysis.
Product data, saved-pick operations and legacy analysis/odds APIs require
Premium; profile, canonical subscription state and billing remain available to
free or lapsed accounts. Existing analytical/administrative role checks are not
replaced by a purchase.
Mixed team/sport metadata routers protect their intelligence endpoints
individually. Legacy result/model-analysis reads cannot bypass the entitlement
gate. Previously unguarded pipeline/job, promotion/runtime/bootstrap, weight,
system and settlement controls, plus result creation, now require existing
admin authorization. This changes request authorization only; it does not
change their calculations, settlement implementation or worker execution.

## Approved sandbox offers

The shared server configuration exposed at `/api/v1/subscriptions/plans` is:

| Plan | Renewal price | Interval | Trial |
| --- | --- | --- | --- |
| `pro_monthly` | USD 10.00 | Monthly | Seven days |
| `pro_annual` | USD 79.99 | Annually | Seven days |

The frontend formats these minor-unit amounts and uses the same benefits and
trial definition. Before creating checkout, the backend verifies that the
configured Stripe **test** price is active, not live, and matches amount,
currency and recurrence. A mismatch fails closed; no checkout session is
created. Taxes, refunds and any jurisdiction-specific obligations require
separate product/legal review; no tax or refund policy is inferred.
Checkout rejects an existing active canonical Premium entitlement, including
trial access and access from another provider, with HTTP 409 before contacting
Stripe. Plan controls stay disabled while access is loading, unavailable, or
active; billing management remains available. Expired/inactive accounts may
start checkout. This does not reserve or deduplicate concurrent checkouts for
accounts that do not yet have an active entitlement.

Stripe remains test-mode-only and disabled by default. Live keys are rejected.
No customer-facing offer is permission to enable live charges.

## Stripe event ordering

Verified event IDs remain durably idempotent. A nullable provider-created UTC
timestamp records chronology without inventing timestamps for existing rows.
PostgreSQL transaction advisory locks serialize processing per subscription,
including its first event, and entitlement reconciliation per user across
concurrent subscriptions. Retrieved provider responses must match the requested
subscription identity. Older events are durably ignored after a later
processed event. Same-second events, missing chronology and legacy-state
boundaries retrieve the current provider subscription rather than guessing
event-ID order. Checkout and invoice events also reconcile current subscription
state. Failed events remain retryable but cannot overwrite newer chronology.
An existing subscription cannot change owner through webhook metadata.
The pinned Stripe SDK uses subscription-item billing periods. Both that
representation and legacy top-level periods are supported; missing or
ambiguous item periods fail closed instead of creating an unbounded active
entitlement. Trial access is bounded by its provider trial end; cancellation
can revoke access even when billing-period fields are absent.

Adding chronology does not rewrite subscriptions, entitlements or historical
event records. Existing null chronology is resolved on a future verified event
through the provider's current test-mode state. No migration calls Stripe.

## Authentication cutover and validation

See the [durable authentication guide](../backend/docs/durable-auth.md) for
verification delivery, cleanup bounds and operational cutover details.

The migration chain is `e7b4c2d9a610` -> `f8a1d3c6b920` (durable auth) ->
`a9b2e4d7c031` (provider chronology). The auth migration adds six new tables;
it does not rewrite existing users. Every access JWT must have a matching
durable hashed access-session record. Refresh sessions, revocations,
login-failure/lockout records, one-time tokens and address-bound verification
state also survive process replacement.
Verification issuance timestamps enforce a recipient-level 60-second cooldown
across process replacement. Suppressed requests keep neutral responses and
preserve the existing link; both registration paths queue initial delivery.

Memory-only session history cannot safely be reconstructed: all pre-cutover
access and refresh tokens fail closed and customers must sign in again.
There is no invented session backfill or timestamp cutoff ambiguity. Password
reset/change invalidates all of the account's access and refresh records.
User-level locking serializes password changes with login/refresh; conditional
refresh rotation prevents multiple concurrent winners. Do not deploy schema
and authentication code independently. Auth downgrade removes the new auth
records and also requires reauthentication; it is not a session-preserving
rollback.

Validation must use synthetic SQLite/disposable PostgreSQL, mocked mail and
Stripe test fixtures, with outbound network blocked. A positive local test
does not certify actual SMTP delivery, provider price setup, legal approval or
production operation. Production, retention decisions and previous audit
records must remain untouched.

## Remaining approval gates

- Attorney review of Terms, Privacy, responsible-gaming, disclaimer, trial,
  renewal, cancellation and refund language.
- Confirm support mailbox ownership, staffing and response expectations.
- Confirm the configured Stripe sandbox prices match approved offers.
- Review auth/chronology migrations and forced-login impact before rollout.
- Separately approve any real-provider sandbox exercise or future production
  deployment. Live billing requires a separately reviewed implementation.
- No retention scheduling or apply-mode approval is included.
