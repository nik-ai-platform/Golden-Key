"""Durable authentication state; bearer credentials are never stored."""

import time

from sqlalchemy import BigInteger, Boolean, Column, ForeignKey, Integer, String

from app.database.base import Base


class RefreshSession(Base):
    __tablename__ = "auth_refresh_sessions"

    token_digest = Column(String(64), primary_key=True)
    # The configured demo identity uses id=0 and has no users row.
    user_id = Column(Integer, nullable=False)
    expires_at = Column(BigInteger, nullable=False, index=True)
    revoked = Column(Boolean, nullable=False, default=False)


class AccessSession(Base):
    __tablename__ = "auth_access_sessions"

    token_digest = Column(String(64), primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    expires_at = Column(BigInteger, nullable=False, index=True)
    revoked = Column(Boolean, nullable=False, default=False)


class RevokedToken(Base):
    __tablename__ = "auth_revoked_tokens"

    token_digest = Column(String(64), primary_key=True)
    expires_at = Column(BigInteger, nullable=False, index=True)


class LoginFailure(Base):
    __tablename__ = "auth_login_failures"

    subject_digest = Column(String(64), primary_key=True)
    attempts = Column(Integer, nullable=False, default=0)
    locked_until = Column(BigInteger, nullable=True)
    expires_at = Column(BigInteger, nullable=False, index=True)


class EmailVerificationToken(Base):
    __tablename__ = "auth_email_verification_tokens"

    token_digest = Column(String(64), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(320), nullable=False)
    issued_at = Column(BigInteger, nullable=False, default=lambda: int(time.time()))
    expires_at = Column(BigInteger, nullable=False, index=True)


class VerifiedEmail(Base):
    __tablename__ = "auth_verified_emails"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    email = Column(String(320), nullable=False)
    verified_at = Column(BigInteger, nullable=False)


EXPIRING_AUTH_MODELS = (AccessSession, RefreshSession, RevokedToken, LoginFailure, EmailVerificationToken)
AUTH_STATE_MODELS = (*EXPIRING_AUTH_MODELS, VerifiedEmail)
