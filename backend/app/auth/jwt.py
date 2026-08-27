from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from jwt import DecodeError
from jwt import ExpiredSignatureError
from jwt import InvalidTokenError

from app.core.config import settings


class JWTError(Exception):
    pass


class JWTService:
    def __init__(
        self,
        *,
        secret_key: str | None = None,
        algorithm: str | None = None,
        access_token_minutes: int | None = None,
    ):
        self.secret_key = secret_key or settings.JWT_SECRET_KEY
        self.algorithm = algorithm or settings.JWT_ALGORITHM
        self.access_token_minutes = (
            access_token_minutes
            if access_token_minutes is not None
            else settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )


    def _encode(
        self,
        payload: dict,
        *,
        expires_delta: timedelta,
        token_type: str,
    ) -> tuple[str, int, str]:
        now = datetime.now(timezone.utc)
        jti = str(uuid4())
        expires_epoch = int((now + expires_delta).timestamp())
        data = {
            **payload,
            "type": token_type,
            "jti": jti,
            "iat": int(now.timestamp()),
            "exp": expires_epoch,
        }
        return jwt.encode(data, self.secret_key, algorithm=self.algorithm), expires_epoch, jti


    def create_access_token(
        self,
        payload: dict,
        expires_delta: timedelta | None = None,
    ) -> tuple[str, int, str]:
        effective_delta = expires_delta or timedelta(minutes=self.access_token_minutes)
        return self._encode(payload, expires_delta=effective_delta, token_type="access")


    def create_refresh_token(
        self,
        payload: dict,
        expires_delta: timedelta,
    ) -> tuple[str, int, str]:
        return self._encode(payload, expires_delta=expires_delta, token_type="refresh")


    def decode_access_token(self, token: str) -> dict:
        try:
            return jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_aud": False},
            )
        except ExpiredSignatureError as exc:
            raise JWTError("Token expired") from exc
        except DecodeError as exc:
            raise JWTError("Invalid token format") from exc
        except InvalidTokenError as exc:
            message = str(exc)
            if "signature" in message.lower():
                raise JWTError("Invalid token signature") from exc
            raise JWTError("Invalid token format") from exc


    def validate_access_token(self, token: str) -> dict:
        payload = self.decode_access_token(token)

        if payload.get("type") != "access":
            raise JWTError("Invalid token type")

        if not payload.get("sub"):
            raise JWTError("Token missing subject")

        return payload


    def validate_refresh_token(self, token: str) -> dict:
        payload = self.decode_access_token(token)
        if payload.get("type") != "refresh":
            raise JWTError("Invalid token type")
        if not payload.get("sub"):
            raise JWTError("Token missing subject")
        return payload
