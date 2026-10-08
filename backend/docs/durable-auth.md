# Durable customer authentication

Apply migration `f8a1d3c6b920` (parent `e7b4c2d9a610`) before deploying the
authentication changes. It creates six empty auth tables without touching
customer/business records. Existing process-memory refresh sessions and
verification links cannot be backfilled and are invalid: customers must sign in
again. Every access JWT must also match a persisted hashed identifier in
`auth_access_sessions`; all pre-migration access tokens fail closed regardless
of their signature or expiration, including tokens whose old memory revocation
cannot be reconstructed. No clock-sensitive cutoff is needed. Password reset
and password change revoke all persisted access/refresh sessions for that user
in the same transaction as the password update. Downgrade
destroys durable auth state and should only be performed after stopping auth
traffic and invalidating outstanding JWTs through an approved signing-key rotation.

Refresh identifiers, revoked JWT identifiers, and random 256-bit verification
tokens are stored as SHA-256 digests, not bearer credentials. Refresh rotation
conditionally revokes the old row and inserts the new row in one transaction.
Lockout counts use database-native upserts on PostgreSQL and SQLite; there is no
process-local fallback. Five failed attempts lock the subject for 15 minutes.
Idle failures expire after 15 minutes. Run the migration for every test database
or create the six models in isolated synthetic SQLite fixtures. Verified sign-in
addresses are persisted separately in `auth_verified_emails`, bound to the
current user ID and address; no nonexistent `users.email_verified` field or
untrusted legacy flags are backfilled. Address changes automatically stop matching
the stored verification. Verified state survives auth cleanup.

`POST /api/v1/auth/email-verification` and the additive
`POST /api/v1/auth/email-verification/resend` accept `{"email": "..."}` and return
the same neutral message for nonexistent, verified, inactive, and eligible
accounts, including requests within the 60-second recipient cooldown. The token's
`issued_at` is stored in PostgreSQL; the user-row lock serializes concurrent
requests across processes. Requests during cooldown neither queue mail nor
invalidate the current link. After 60 seconds, an eligible request supersedes
old links. Both `/auth/register` and onboarding registration queue the first
verification and start the same cooldown. Delivery is queued through FastAPI
BackgroundTasks and the existing mail sender abstraction; it is not a durable
mail outbox. Failed mail delivery logs no address or token; a resend can retry.
Links target `/verify-email?token=...`; submit that opaque token to the existing
`POST /api/v1/auth/email-verification/confirm` endpoint. It expires after 60 minutes
and can only verify the unchanged sign-in address once. Never log the link/token.
The service returns an `EmailVerificationDelivery` for callers (including
registration and onboarding) to queue with `deliver_email_verification`; it never sends synchronously.
No sign-in address-change endpoint is introduced.

## Customer mail identity

The intended customer sender is
`Bear A Hand Sports Support <owner@bearahandllc.com>`. Configure `SMTP_SETTINGS`
with separate `from_email` (`owner@bearahandllc.com`) and `from_name`
(`Bear A Hand Sports Support`) fields; do not place a formatted display name
in `from_email`. Use the public mailbox as the SMTP username. The optional
`from_name` preserves address-only headers when omitted by existing installations.
All four authentication message types use the same sender configuration.

Environment examples contain placeholders, not validated provider settings or
credentials. Confirm the SMTP host, port and encryption in the mailbox provider.
The current sender supports SMTP with STARTTLS (`use_tls: true`, commonly port
587); it does not implement implicit SMTPS/SSL on port 465. Never disable TLS
to work around a provider mismatch. Real delivery requires a separately approved
secrets update and delivery check; this hotfix performs neither.
Keep private administrator credentials separate from public support identity.
Mailbox send/receive tests, available two-factor authentication, unique passwords,
domain authorization and actual delivery are still unverified.

Explicit maintenance, from the backend directory with the configured Python
environment and `PYTHONPATH` including that directory:

```powershell
python scripts\cleanup_expired_auth.py --batch-size 500
```

Each invocation deletes at most the requested number of expired rows **per
expiring auth table** (five tables; maximum 10,000 per table) in a single transaction and emits counts
only. Revoked refresh rows remain until original expiration to prevent replay.
No scheduler, worker, telemetry, retention registry, or business-data cleanup is
installed. Existing password-reset and recovery-code tables are not touched.

Validation: focused SQLite tests cover API compatibility, fake-only mail,
verification/revocation persistence, bounded cleanup, and migration semantics.
`tests\test_durable_auth_postgres.py` is opt-in with `AUTH_TEST_POSTGRES_URL`;
it rejects non-loopback hosts and databases other than `launch_validation`,
creates/deletes private random schemas, and validates actual PostgreSQL
migration upgrade/downgrade, fresh-instance persistence, and multiprocess refresh
rotation/login upserts. It does not migrate the fixture's public schema. The
isolated users fixture adjusts a copied DDL default to the ORM enum name
`VIEWER`; the pre-existing User ORM default uses lowercase `viewer`, incompatible
with its generated name-based PostgreSQL enum. No production users schema is
altered by this test workaround or the auth migration.
