import hashlib
import logging
import secrets
from dataclasses import dataclass
from types import SimpleNamespace
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth.hashing import HashingService
from app.auth.jwt import JWTError, JWTService
from app.auth.session_store import session_store
from app.auth.schemas import AccessTokenResponse, AuthUser
from app.core.config import settings
from app.core.roles import UserRole
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.mail_service import MailSender, SmtpMailSender
from app.services.performance_metrics_service import performance_metrics


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PasswordResetDelivery:
    recipient: str
    token: str


class AuthenticationService:
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
        if session_store.is_locked(email.lower()):
            performance_metrics.record_auth_failure("lockout", email.lower())
            return None

        user = self._resolve_user(db, email)
        if user is None:
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

        access_token, access_exp, _ = self.jwt_service.create_access_token(
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
        session_store.create_refresh_session(refresh_jti, int(user.id), refresh_exp)

        return AccessTokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=max(0, access_exp - int(datetime.now(UTC).timestamp())),
            refresh_expires_in=max(0, refresh_exp - int(datetime.now(UTC).timestamp())),
        )

    def refresh(self, db: Session, refresh_token: str) -> AccessTokenResponse:
        payload = self.jwt_service.validate_refresh_token(refresh_token)
        jti = str(payload.get("jti", ""))
        if not jti or not session_store.is_refresh_session_active(jti):
            raise JWTError("Refresh token revoked")

        user = self._resolve_user(db, str(payload.get("sub", "")))
        if user is None or not user.is_active:
            raise JWTError("User not found")

        access_token, access_exp, _ = self.jwt_service.create_access_token(
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
        session_store.revoke_refresh_session(jti)
        session_store.create_refresh_session(refresh_jti, int(user.id), refresh_exp)

        return AccessTokenResponse(
            access_token=access_token,
            refresh_token=new_refresh,
            token_type="bearer",
            expires_in=max(0, access_exp - int(datetime.now(UTC).timestamp())),
            refresh_expires_in=max(0, refresh_exp - int(datetime.now(UTC).timestamp())),
        )

    def revoke_session(self, access_token: str, refresh_token: str | None = None) -> None:
        access_payload = self.jwt_service.validate_access_token(access_token)
        access_jti = str(access_payload.get("jti", ""))
        access_exp = int(access_payload.get("exp", 0) or 0)
        if access_jti and access_exp:
            session_store.revoke_jti(access_jti, access_exp)

        if refresh_token:
            refresh_payload = self.jwt_service.validate_refresh_token(refresh_token)
            refresh_jti = str(refresh_payload.get("jti", ""))
            refresh_exp = int(refresh_payload.get("exp", 0) or 0)
            if refresh_jti:
                session_store.revoke_refresh_session(refresh_jti)
                session_store.revoke_jti(refresh_jti, refresh_exp)

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

        user = db.get(User, reset_token.user_id)
        if user is None or not user.is_active:
            return False

        user.hashed_password = self.hashing_service.hash_password(new_password)
        reset_token.used_at = now
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        ).update({PasswordResetToken.used_at: now}, synchronize_session=False)
        db.add(user)
        db.commit()
        session_store.clear_failed_logins(user.email.lower())
        return True

    @staticmethod
    def _reset_token_digest(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def request_email_verification(self, db: Session, email: str) -> None:
        user = self._resolve_user(db, email)
        if user is None:
            return
        verify_token, _, _ = self.jwt_service.create_access_token(
            {"sub": user.email, "uid": user.id},
            expires_delta=timedelta(minutes=60),
        )
        session_store.create_email_verification(verify_token, user.email, 60)

    def verify_email(self, db: Session, token: str) -> bool:
        email = session_store.consume_email_verification(token)
        if not email:
            return False

        user = self._resolve_user(db, email)
        if user is None or getattr(user, "id", 0) == 0:
            return False

        if hasattr(user, "email_verified"):
            user.email_verified = True
            db.add(user)
            db.commit()
        return True

    def current_user(
        self,
        db: Session,
        token: str,
    ) -> AuthUser:
        payload = self.jwt_service.validate_access_token(token)
        jti = str(payload.get("jti", ""))
        if jti and session_store.is_revoked(jti):
            raise JWTError("Token revoked")
        email = payload.get("sub")

        user = self._resolve_user(db, email)
        if user is None:
            raise JWTError("User not found")

        if not user.is_active:
            raise JWTError("Inactive user")

        return AuthUser(
            id=user.id,
            username=user.username,
            email=user.email,
            role=UserRole(self._role_value(user.role)),
            is_active=user.is_active,
            email_verified=bool(getattr(user, "email_verified", False)),
        )


AuthService = AuthenticationService
