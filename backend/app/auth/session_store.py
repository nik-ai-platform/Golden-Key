from __future__ import annotations

from datetime import UTC, datetime, timedelta
from threading import Lock


class SessionStore:
    def __init__(self) -> None:
        self._revoked: dict[str, float] = {}
        self._refresh_sessions: dict[str, dict] = {}
        self._email_verification_tokens: dict[str, dict] = {}
        self._lockout: dict[str, dict] = {}
        self._lock = Lock()

    def revoke_jti(self, jti: str, expires_at_epoch: int) -> None:
        with self._lock:
            self._revoked[jti] = float(expires_at_epoch)

    def is_revoked(self, jti: str) -> bool:
        with self._lock:
            now = datetime.now(UTC).timestamp()
            expired = [key for key, value in self._revoked.items() if value <= now]
            for key in expired:
                self._revoked.pop(key, None)
            return jti in self._revoked

    def create_refresh_session(self, jti: str, user_id: int, expires_at_epoch: int) -> None:
        with self._lock:
            self._refresh_sessions[jti] = {
                "user_id": user_id,
                "expires_at": float(expires_at_epoch),
                "revoked": False,
            }

    def revoke_refresh_session(self, jti: str) -> None:
        with self._lock:
            session = self._refresh_sessions.get(jti)
            if session:
                session["revoked"] = True

    def is_refresh_session_active(self, jti: str) -> bool:
        with self._lock:
            session = self._refresh_sessions.get(jti)
            if not session:
                return False
            if session.get("revoked"):
                return False
            if float(session.get("expires_at", 0)) <= datetime.now(UTC).timestamp():
                return False
            return True

    def register_failed_login(self, subject: str, lock_minutes: int, max_attempts: int) -> tuple[int, bool]:
        with self._lock:
            now = datetime.now(UTC)
            state = self._lockout.get(subject) or {"attempts": 0, "locked_until": None}
            locked_until = state.get("locked_until")
            if locked_until and now < locked_until:
                return int(state.get("attempts", 0)), True

            attempts = int(state.get("attempts", 0)) + 1
            is_locked = attempts >= max_attempts
            self._lockout[subject] = {
                "attempts": attempts,
                "locked_until": now + timedelta(minutes=lock_minutes) if is_locked else None,
            }
            return attempts, is_locked

    def clear_failed_logins(self, subject: str) -> None:
        with self._lock:
            self._lockout.pop(subject, None)

    def is_locked(self, subject: str) -> bool:
        with self._lock:
            now = datetime.now(UTC)
            state = self._lockout.get(subject)
            if not state:
                return False
            locked_until = state.get("locked_until")
            if not locked_until:
                return False
            if now >= locked_until:
                self._lockout.pop(subject, None)
                return False
            return True

    def create_email_verification(self, token: str, email: str, expires_in_minutes: int) -> None:
        with self._lock:
            expiry = datetime.now(UTC) + timedelta(minutes=expires_in_minutes)
            self._email_verification_tokens[token] = {"email": email, "expires_at": expiry}

    def consume_email_verification(self, token: str) -> str | None:
        with self._lock:
            state = self._email_verification_tokens.pop(token, None)
            if not state:
                return None
            if datetime.now(UTC) >= state["expires_at"]:
                return None
            return str(state["email"])


session_store = SessionStore()
