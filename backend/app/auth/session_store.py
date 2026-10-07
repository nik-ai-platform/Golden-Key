from __future__ import annotations

import hashlib
import time

from sqlalchemy import case, delete, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.models.auth_state import (
    EXPIRING_AUTH_MODELS,
    AccessSession,
    EmailVerificationToken,
    LoginFailure,
    RefreshSession,
    RevokedToken,
    VerifiedEmail,
)


class SessionStore:
    """Request-bound durable store. Missing schema fails closed, never in memory."""

    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def digest(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _insert(self, model):
        dialect = self.db.get_bind().dialect.name
        if dialect == "postgresql":
            return pg_insert(model)
        if dialect == "sqlite":
            return sqlite_insert(model)
        raise RuntimeError("Authentication persistence requires PostgreSQL or SQLite")

    def revoke_jti(self, jti: str, expires_at_epoch: int) -> None:
        statement = self._insert(RevokedToken).values(
            token_digest=self.digest(jti), expires_at=expires_at_epoch
        )
        self.db.execute(statement.on_conflict_do_nothing())

    def is_revoked(self, jti: str) -> bool:
        return self.db.execute(
            select(RevokedToken.token_digest).where(
                RevokedToken.token_digest == self.digest(jti),
                RevokedToken.expires_at > int(time.time()),
            )
        ).first() is not None

    def create_refresh_session(self, jti: str, user_id: int, expires_at_epoch: int) -> None:
        self.db.add(RefreshSession(
            token_digest=self.digest(jti), user_id=user_id,
            expires_at=expires_at_epoch, revoked=False,
        ))

    def create_access_session(self, jti: str, user_id: int, expires_at_epoch: int) -> None:
        self.db.add(AccessSession(
            token_digest=self.digest(jti), user_id=user_id,
            expires_at=expires_at_epoch, revoked=False,
        ))

    def is_access_session_active(self, jti: str, user_id: int) -> bool:
        return self.db.execute(select(AccessSession.token_digest).where(
            AccessSession.token_digest == self.digest(jti),
            AccessSession.user_id == user_id,
            AccessSession.revoked.is_(False),
            AccessSession.expires_at > int(time.time()),
        )).first() is not None

    def revoke_user_sessions(self, user_id: int) -> None:
        for model in (AccessSession, RefreshSession):
            self.db.execute(update(model).where(model.user_id == user_id).values(revoked=True))

    def revoke_refresh_session(self, jti: str) -> None:
        self.db.execute(update(RefreshSession).where(
            RefreshSession.token_digest == self.digest(jti)
        ).values(revoked=True))

    def is_refresh_session_active(self, jti: str) -> bool:
        return self.db.execute(select(RefreshSession.token_digest).where(
            RefreshSession.token_digest == self.digest(jti),
            RefreshSession.revoked.is_(False),
            RefreshSession.expires_at > int(time.time()),
        )).first() is not None

    def rotate_refresh_session(
        self, old_jti: str, new_jti: str, user_id: int, expires_at_epoch: int
    ) -> bool:
        # Conditional UPDATE serializes competing refreshes on PostgreSQL and SQLite.
        result = self.db.execute(update(RefreshSession).where(
            RefreshSession.token_digest == self.digest(old_jti),
            RefreshSession.user_id == user_id,
            RefreshSession.revoked.is_(False),
            RefreshSession.expires_at > int(time.time()),
        ).values(revoked=True))
        if result.rowcount != 1:
            return False
        self.create_refresh_session(new_jti, user_id, expires_at_epoch)
        return True

    def register_failed_login(self, subject: str, lock_minutes: int, max_attempts: int) -> tuple[int, bool]:
        now = int(time.time())
        expiry = now + lock_minutes * 60
        active_lock = LoginFailure.locked_until > now
        attempts = case(
            (active_lock, LoginFailure.attempts),
            (LoginFailure.expires_at <= now, 1),
            else_=LoginFailure.attempts + 1,
        )
        statement = self._insert(LoginFailure).values(
            subject_digest=self.digest(subject), attempts=1,
            locked_until=expiry if max_attempts <= 1 else None, expires_at=expiry,
        ).on_conflict_do_update(
            index_elements=[LoginFailure.subject_digest],
            set_={
                "attempts": attempts,
                "locked_until": case(
                    (active_lock, LoginFailure.locked_until),
                    (attempts >= max_attempts, expiry),
                    else_=None,
                ),
                "expires_at": case((active_lock, LoginFailure.expires_at), else_=expiry),
            },
        ).returning(LoginFailure.attempts, LoginFailure.locked_until)
        count, locked_until = self.db.execute(statement).one()
        self.db.commit()
        return int(count), locked_until is not None and locked_until > now

    def clear_failed_logins(self, subject: str) -> None:
        self.db.execute(delete(LoginFailure).where(
            LoginFailure.subject_digest == self.digest(subject)
        ))

    def is_locked(self, subject: str) -> bool:
        return self.db.execute(select(LoginFailure.subject_digest).where(
            LoginFailure.subject_digest == self.digest(subject),
            LoginFailure.locked_until > int(time.time()),
        )).first() is not None

    def create_email_verification(self, token: str, user_id: int, email: str, expires_in_minutes: int) -> None:
        self.db.execute(delete(EmailVerificationToken).where(
            EmailVerificationToken.user_id == user_id
        ))
        self.db.add(EmailVerificationToken(
            token_digest=self.digest(token), user_id=user_id, email=email,
            issued_at=int(time.time()),
            expires_at=int(time.time()) + expires_in_minutes * 60,
        ))

    def email_verification_on_cooldown(self, user_id: int, email: str) -> bool:
        return self.db.execute(select(EmailVerificationToken.token_digest).where(
            EmailVerificationToken.user_id == user_id,
            EmailVerificationToken.email == email,
            EmailVerificationToken.issued_at > int(time.time()) - 60,
        )).first() is not None

    def consume_email_verification(self, token: str) -> tuple[int, str] | None:
        row = self.db.execute(delete(EmailVerificationToken).where(
            EmailVerificationToken.token_digest == self.digest(token),
            EmailVerificationToken.expires_at > int(time.time()),
        ).returning(EmailVerificationToken.user_id, EmailVerificationToken.email)).first()
        return (int(row[0]), str(row[1])) if row else None

    def is_email_verified(self, user_id: int, email: str) -> bool:
        return self.db.execute(select(VerifiedEmail.user_id).where(
            VerifiedEmail.user_id == user_id, VerifiedEmail.email == email
        )).first() is not None

    def mark_email_verified(self, user_id: int, email: str) -> None:
        statement = self._insert(VerifiedEmail).values(
            user_id=user_id, email=email, verified_at=int(time.time())
        )
        self.db.execute(statement.on_conflict_do_update(
            index_elements=[VerifiedEmail.user_id],
            set_={"email": email, "verified_at": int(time.time())},
        ))

    def cleanup_expired(self, *, batch_size: int = 500, now: int | None = None) -> dict[str, int]:
        """Delete at most batch_size expired rows per table in one transaction."""
        if not 1 <= batch_size <= 10_000:
            raise ValueError("batch_size must be between 1 and 10000")
        cutoff = int(time.time()) if now is None else now
        counts = {}
        for model in EXPIRING_AUTH_MODELS:
            key = list(model.__table__.primary_key.columns)[0]
            expired = select(key).where(model.expires_at <= cutoff).order_by(
                model.expires_at, key
            ).limit(batch_size)
            result = self.db.execute(delete(model).where(key.in_(expired)))
            counts[model.__tablename__] = result.rowcount
        self.db.commit()
        return counts
