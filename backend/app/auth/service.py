import hashlib
import hmac
import logging
import secrets
from dataclasses import dataclass
from types import SimpleNamespace
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth.hashing import HashingService
from app.auth.jwt import JWTError, JWTService
from app.auth.session_store import SessionStore
from app.auth.schemas import AccessTokenResponse, AuthUser
from app.core.config import settings
from app.core.roles import UserRole
from app.models.password_reset_token import PasswordResetToken
from app.models.auth_state import EmailVerificationToken
from app.models.forgot_email_challenge import ForgotEmailChallenge
from app.models.recovery_email_verification import RecoveryEmailVerification
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.mail_service import MailSender, SmtpMailSender
from app.services.performance_metrics_service import performance_metrics


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PasswordResetDelivery:
    recipient: str
    token: str


@dataclass(frozen=True)
class RecoveryCodeDelivery:
    recipient: str
    code: str


@dataclass(frozen=True)
class EmailVerificationDelivery:
    recipient: str
    token: str


class AuthenticationService:
    recovery_code_expiry = timedelta(minutes=10)
    recovery_code_max_attempts = 5

    def __init__(
        self,
        user_repository: UserRepository | None = None,
        hashing_service: HashingService | None = None,
        jwt_service: JWTService | None = None,
        mail_sender: MailSender | None = None,
    ):
        self.user_repository = user_repository or UserRepository()
        self.hashing_service = hashing_service or HashingService()
        self.jwt_service = jwt_service or JWTService()
        self.mail_sender = mail_sender or SmtpMailSender()
        self._demo_password_hash = self.hashing_service.hash_password(
            settings.AUTH_DEMO_PASSWORD
        )
        self.max_failed_attempts = 5
        self.lockout_minutes = 15

    def _demo_user(self):
        return SimpleNamespace(
            id=0,
            username=settings.AUTH_DEMO_EMAIL.split("@", 1)[0],
            email=settings.AUTH_DEMO_EMAIL.lower(),
            hashed_password=self._demo_password_hash,
            role=UserRole.ADMIN,
            is_active=True,
        )

    def _role_value(self, role: UserRole | str) -> str:
        return role.value if isinstance(role, UserRole) else role

    def _resolve_user(
        self,
        db: Session,
        email: str,
    ):
        if email.lower() == settings.AUTH_DEMO_EMAIL.lower():
            return self._demo_user()

        try:
            user = self.user_repository.get_by_email(db, email.lower())
        except SQLAlchemyError:
            # Treat lookup failures as unknown users to keep auth responses stable.
            return None

        if user:
            return user

        return None

    def authenticate(
        self,
        db: Session,
        email: str,
        password: str,
    ):
        session_store = SessionStore(db)
        if session_store.is_locked(email.lower()):
            performance_metrics.record_auth_failure("lockout", email.lower())
            return None

        user = self._resolve_user(db, email)
        if isinstance(user, User):
            user = db.query(User).filter(User.id == user.id).populate_existing().with_for_update().first()
        if user is None:
            self.hashing_service.verify_password(password, self._demo_password_hash)
            attempts, _ = session_store.register_failed_login(email.lower(), self.lockout_minutes, self.max_failed_attempts)
            performance_metrics.record_auth_failure("unknown_user", email.lower(), attempts)
            return None

        if not user.is_active:
            performance_metrics.record_auth_failure("inactive", email.lower())
            return None

        if not self.hashing_service.verify_password(
            password,
            user.hashed_password,
        ):
            attempts, is_locked = session_store.register_failed_login(email.lower(), self.lockout_minutes, self.max_failed_attempts)
            reason = "locked" if is_locked else "bad_password"
            performance_metrics.record_auth_failure(reason, email.lower(), attempts)
            return None

        session_store.clear_failed_logins(email.lower())
        return user

    def login(
        self,
        db: Session,
        email: str,
        password: str,
    ) -> AccessTokenResponse | None:
        user = self.authenticate(db, email, password)
        if user is None:
            return None

        access_token, access_exp, access_jti = self.jwt_service.create_access_token(
            {
                "sub": user.email,
                "role": self._role_value(user.role),
                "uid": user.id,
            }
        )

        refresh_token, refresh_exp, refresh_jti = self.jwt_service.create_refresh_token(
            {
                "sub": user.email,
                "role": self._role_value(user.role),
                "uid": user.id,
            },
            expires_delta=timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES),
        )
        SessionStore(db).create_refresh_session(refresh_jti, int(user.id), refresh_exp)
        SessionStore(db).create_access_session(access_jti, int(user.id), access_exp)
        db.commit()

        return AccessTokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=max(0, access_exp - int(datetime.now(UTC).timestamp())),
            refresh_expires_in=max(0, refresh_exp - int(datetime.now(UTC).timestamp())),
        )

    def refresh(self, db: Session, refresh_token: str) -> AccessTokenResponse:
        session_store = SessionStore(db)
        payload = self.jwt_service.validate_refresh_token(refresh_token)
        jti = str(payload.get("jti", ""))
        if not jti or not session_store.is_refresh_session_active(jti):
            raise JWTError("Refresh token revoked")

        user = self._resolve_user(db, str(payload.get("sub", "")))
        if isinstance(user, User):
            # Password updates take this same lock before revoking session rows.
            # The conditional rotation below revalidates after acquiring it.
            user = db.query(User).filter(User.id == user.id).populate_existing().with_for_update().first()
        if user is None or not user.is_active:
            raise JWTError("User not found")

        access_token, access_exp, access_jti = self.jwt_service.create_access_token(
            {
                "sub": user.email,
                "role": self._role_value(user.role),
                "uid": user.id,
            }
        )

        new_refresh, refresh_exp, refresh_jti = self.jwt_service.create_refresh_token(
            {
                "sub": user.email,
                "role": self._role_value(user.role),
                "uid": user.id,
            },
            expires_delta=timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES),
        )
        if not session_store.rotate_refresh_session(jti, refresh_jti, int(user.id), refresh_exp):
            db.rollback()
            raise JWTError("Refresh token revoked")
        session_store.create_access_session(access_jti, int(user.id), access_exp)
        db.commit()

        return AccessTokenResponse(
            access_token=access_token,
            refresh_token=new_refresh,
            token_type="bearer",
            expires_in=max(0, access_exp - int(datetime.now(UTC).timestamp())),
            refresh_expires_in=max(0, refresh_exp - int(datetime.now(UTC).timestamp())),
        )

    def revoke_session(self, db: Session, access_token: str, refresh_token: str | None = None) -> None:
        session_store = SessionStore(db)
        access_payload = self.jwt_service.validate_access_token(access_token)
        refresh_payload = None
        if refresh_token:
            refresh_payload = self.jwt_service.validate_refresh_token(refresh_token)
            if refresh_payload.get("uid") != access_payload.get("uid") or refresh_payload.get("sub") != access_payload.get("sub"):
                raise JWTError("Session does not belong to user")
        access_jti = str(access_payload.get("jti", ""))
        access_exp = int(access_payload.get("exp", 0) or 0)
        if access_jti and access_exp:
            session_store.revoke_jti(access_jti, access_exp)

        if refresh_payload:
            refresh_jti = str(refresh_payload.get("jti", ""))
            refresh_exp = int(refresh_payload.get("exp", 0) or 0)
            if refresh_jti:
                session_store.revoke_refresh_session(refresh_jti)
                session_store.revoke_jti(refresh_jti, refresh_exp)
        db.commit()

    def request_password_reset(
        self,
        db: Session,
        email: str,
    ) -> PasswordResetDelivery | None:
        user = self._resolve_user(db, email)
        if user is None or getattr(user, "id", 0) == 0:
            return None

        now = datetime.now(UTC)
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        ).update({PasswordResetToken.used_at: now}, synchronize_session=False)
        token = secrets.token_urlsafe(32)
        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_digest=self._reset_token_digest(token),
                expires_at=now + timedelta(minutes=20),
            )
        )
        db.commit()
        return PasswordResetDelivery(recipient=user.email, token=token)

    def deliver_password_reset(self, delivery: PasswordResetDelivery) -> None:
        try:
            self.mail_sender.send_password_reset(delivery.recipient, delivery.token)
        except Exception:  # noqa: BLE001
            logger.error("Password reset email delivery failed")

    def request_recovery_email_verification(
        self,
        db: Session,
        user_id: int,
        recovery_email: str,
    ) -> RecoveryCodeDelivery:
        normalized_email = recovery_email.strip().lower()
        user = db.get(User, user_id)
        if user is None or not user.is_active:
            raise ValueError("Unable to configure recovery email")
        if normalized_email == user.email.lower():
            raise ValueError("Recovery email must differ from sign-in email")
        owner = db.query(User).filter(User.recovery_email == normalized_email).first()
        if owner is not None and owner.id != user.id:
            raise ValueError("Unable to configure recovery email")

        now = datetime.now(UTC)
        db.query(RecoveryEmailVerification).filter(
            RecoveryEmailVerification.user_id == user.id,
            RecoveryEmailVerification.used_at.is_(None),
        ).update({RecoveryEmailVerification.used_at: now}, synchronize_session=False)
        code = self._new_recovery_code()
        user.recovery_email = normalized_email
        user.recovery_email_verified = False
        db.add(
            RecoveryEmailVerification(
                user_id=user.id,
                recovery_email=normalized_email,
                code_digest=self._recovery_code_digest(
                    "recovery-email-verification", user.id, normalized_email, code
                ),
                expires_at=now + self.recovery_code_expiry,
            )
        )
        db.add(user)
        db.commit()
        return RecoveryCodeDelivery(recipient=normalized_email, code=code)

    def deliver_recovery_email_verification(self, delivery: RecoveryCodeDelivery) -> None:
        try:
            self.mail_sender.send_recovery_email_verification(delivery.recipient, delivery.code)
        except Exception:  # noqa: BLE001
            logger.error("Recovery email verification delivery failed")

    def verify_recovery_email(self, db: Session, user_id: int, code: str) -> bool:
        user = db.get(User, user_id)
        if user is None or not user.recovery_email:
            return False
        now = datetime.now(UTC)
        challenge = (
            db.query(RecoveryEmailVerification)
            .filter(
                RecoveryEmailVerification.user_id == user.id,
                RecoveryEmailVerification.recovery_email == user.recovery_email,
                RecoveryEmailVerification.used_at.is_(None),
                RecoveryEmailVerification.expires_at > now,
            )
            .order_by(RecoveryEmailVerification.created_at.desc())
            .first()
        )
        if challenge is None or challenge.failed_attempts >= self.recovery_code_max_attempts:
            return False
        expected = self._recovery_code_digest(
            "recovery-email-verification", user.id, user.recovery_email, code
        )
        if not hmac.compare_digest(challenge.code_digest, expected):
            self._record_failed_recovery_attempt(db, challenge, now)
            return False

        challenge.used_at = now
        user.recovery_email_verified = True
        db.add_all([challenge, user])
        db.commit()
        return True

    def request_forgot_email(
        self, db: Session, recovery_email: str
    ) -> RecoveryCodeDelivery | None:
        normalized_email = recovery_email.strip().lower()
        user = (
            db.query(User)
            .filter(
                User.recovery_email == normalized_email,
                User.recovery_email_verified.is_(True),
                User.is_active.is_(True),
            )
            .first()
        )
        if user is None:
            return None

        now = datetime.now(UTC)
        db.query(ForgotEmailChallenge).filter(
            ForgotEmailChallenge.user_id == user.id,
            ForgotEmailChallenge.used_at.is_(None),
        ).update({ForgotEmailChallenge.used_at: now}, synchronize_session=False)
        code = self._new_recovery_code()
        db.add(
            ForgotEmailChallenge(
                user_id=user.id,
                recovery_email=normalized_email,
                code_digest=self._recovery_code_digest(
                    "forgot-email", user.id, normalized_email, code
                ),
                expires_at=now + self.recovery_code_expiry,
            )
        )
        db.commit()
        return RecoveryCodeDelivery(recipient=normalized_email, code=code)

    def deliver_forgot_email_code(self, delivery: RecoveryCodeDelivery) -> None:
        try:
            self.mail_sender.send_forgot_email_code(delivery.recipient, delivery.code)
        except Exception:  # noqa: BLE001
            logger.error("Forgot email recovery delivery failed")

    def verify_forgot_email(self, db: Session, recovery_email: str, code: str) -> str | None:
        normalized_email = recovery_email.strip().lower()
        user = (
            db.query(User)
            .filter(
                User.recovery_email == normalized_email,
                User.recovery_email_verified.is_(True),
                User.is_active.is_(True),
            )
            .first()
        )
        if user is None:
            return None
        now = datetime.now(UTC)
        challenge = (
            db.query(ForgotEmailChallenge)
            .filter(
                ForgotEmailChallenge.user_id == user.id,
                ForgotEmailChallenge.recovery_email == normalized_email,
                ForgotEmailChallenge.used_at.is_(None),
                ForgotEmailChallenge.expires_at > now,
            )
            .order_by(ForgotEmailChallenge.created_at.desc())
            .first()
        )
        if challenge is None or challenge.failed_attempts >= self.recovery_code_max_attempts:
            return None
        expected = self._recovery_code_digest("forgot-email", user.id, normalized_email, code)
        if not hmac.compare_digest(challenge.code_digest, expected):
            self._record_failed_recovery_attempt(db, challenge, now)
            return None

        challenge.used_at = now
        db.add(challenge)
        db.commit()
        return self.mask_email(user.email)

    @staticmethod
    def mask_email(email: str) -> str:
        local, separator, domain = email.partition("@")
        if not separator or not local or not domain:
            return "***"
        return f"{local[0]}{'*' * max(1, len(local) - 1)}@{domain}"

    @staticmethod
    def _new_recovery_code() -> str:
        return f"{secrets.randbelow(1_000_000):06d}"

    @staticmethod
    def _recovery_code_digest(purpose: str, user_id: int, email: str, code: str) -> str:
        payload = f"{purpose}:{user_id}:{email}:{code}".encode("utf-8")
        return hmac.new(settings.SECRET_KEY.encode("utf-8"), payload, hashlib.sha256).hexdigest()

    def _record_failed_recovery_attempt(self, db: Session, challenge, now: datetime) -> None:
        challenge.failed_attempts += 1
        if challenge.failed_attempts >= self.recovery_code_max_attempts:
            challenge.used_at = now
        db.add(challenge)
        db.commit()

    def reset_password(self, db: Session, token: str, new_password: str) -> bool:
        if not token:
            return False

        now = datetime.now(UTC)
        reset_token = (
            db.query(PasswordResetToken)
            .filter(
                PasswordResetToken.token_digest == self._reset_token_digest(token),
                PasswordResetToken.used_at.is_(None),
                PasswordResetToken.expires_at > now,
            )
            .with_for_update()
            .first()
        )
        if reset_token is None:
            return False

        user = db.query(User).filter(User.id == reset_token.user_id).populate_existing().with_for_update().first()
        if user is None or not user.is_active:
            return False

        user.hashed_password = self.hashing_service.hash_password(new_password)
        reset_token.used_at = now
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        ).update({PasswordResetToken.used_at: now}, synchronize_session=False)
        db.add(user)
        SessionStore(db).clear_failed_logins(user.email.lower())
        SessionStore(db).revoke_user_sessions(int(user.id))
        db.commit()
        return True

    def change_password(
        self,
        db: Session,
        user: User,
        current_password: str,
        new_password: str,
    ) -> bool:
        user = db.query(User).filter(User.id == user.id).populate_existing().with_for_update().first()
        if user is None or not user.id or not self.hashing_service.verify_password(
            current_password,
            user.hashed_password,
        ):
            return False

        user.hashed_password = self.hashing_service.hash_password(new_password)
        db.add(user)
        SessionStore(db).clear_failed_logins(user.email.lower())
        SessionStore(db).revoke_user_sessions(int(user.id))
        db.commit()
        return True

    @staticmethod
    def _reset_token_digest(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def request_email_verification(self, db: Session, email: str) -> EmailVerificationDelivery | None:
        user = self._resolve_user(db, email)
        if user is None or not user.is_active or not user.id:
            return None
        # Serializes the durable recipient cooldown with resend and confirmation.
        user = db.query(User).filter(User.id == user.id).populate_existing().with_for_update().one()
        if not user.is_active or SessionStore(db).is_email_verified(int(user.id), user.email):
            return None
        if SessionStore(db).email_verification_on_cooldown(int(user.id), user.email):
            return None
        verify_token = secrets.token_urlsafe(32)
        SessionStore(db).create_email_verification(verify_token, int(user.id), user.email, 60)
        db.commit()
        return EmailVerificationDelivery(recipient=user.email, token=verify_token)

    def deliver_email_verification(self, delivery: EmailVerificationDelivery) -> None:
        try:
            self.mail_sender.send_email_verification(delivery.recipient, delivery.token)
        except Exception:  # noqa: BLE001
            logger.error("Sign-in email verification delivery failed")

    def verify_email(self, db: Session, token: str) -> bool:
        if not token:
            return False
        store = SessionStore(db)
        # Lock the user before the token to match resend's lock ordering.
        candidate = db.get(EmailVerificationToken, store.digest(token))
        if candidate is None:
            return False
        user = db.query(User).filter(User.id == candidate.user_id).populate_existing().with_for_update().first()
        state = store.consume_email_verification(token)
        if state is None or user is None or not user.is_active or user.email != state[1]:
            db.rollback()
            return False
        store.mark_email_verified(int(user.id), user.email)
        db.commit()
        return True

    def current_user(
        self,
        db: Session,
        token: str,
    ) -> AuthUser:
        payload = self.jwt_service.validate_access_token(token)
        jti = str(payload.get("jti", ""))
        if jti and SessionStore(db).is_revoked(jti):
            raise JWTError("Token revoked")
        email = payload.get("sub")

        user = self._resolve_user(db, email)
        if user is None:
            raise JWTError("User not found")

        if not user.is_active:
            raise JWTError("Inactive user")
        if not jti or not SessionStore(db).is_access_session_active(jti, int(user.id)):
            raise JWTError("Session expired or revoked")

        return AuthUser(
            id=user.id,
            username=user.username,
            email=user.email,
            role=UserRole(self._role_value(user.role)),
            is_active=user.is_active,
            email_verified=SessionStore(db).is_email_verified(int(user.id), user.email),
            recovery_email_masked=(
                self.mask_email(user.recovery_email) if getattr(user, "recovery_email", None) else None
            ),
            recovery_email_verified=bool(getattr(user, "recovery_email_verified", False)),
        )


AuthService = AuthenticationService
