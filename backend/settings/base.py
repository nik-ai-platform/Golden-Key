from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
ROOT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class BaseAppSettings(BaseSettings):
    APP_NAME: str = "Nik AI Sports Betting Platform"
    VERSION: str = "1.0.0"

    ENVIRONMENT: Literal["development", "testing", "staging", "production"] = Field(
        default="development",
        validation_alias=AliasChoices("ENVIRONMENT", "APP_ENV"),
    )

    DATABASE_URL: str
    DATABASE_REPLICA_URL: str | None = None

    SECRET_KEY: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    FRONTEND_URL: str = "http://localhost:3000"
    CORS_ORIGINS: str = "http://localhost:3000"

    OPENAI_API_KEY: str = ""
    SPORTSBOOK_API_KEYS: dict[str, str] = {}
    ODDS_API_KEY: str
    ODDS_API_BASE_URL: str = "https://api.the-odds-api.com/v4"

    REDIS_URL: str = ""
    STORAGE_BACKEND: str = "local"
    SMTP_SETTINGS: dict[str, Any] = {}

    DB_POOL_SIZE: int = 40
    DB_MAX_OVERFLOW: int = 80
    DB_POOL_TIMEOUT_SECONDS: int = 30
    DB_POOL_RECYCLE_SECONDS: int = 1800
    DB_POOL_PRE_PING: bool = True
    API_URL: str = "http://backend:8000"
    REQUEST_TIMEOUT_SECONDS: float = 20.0
    MAX_REQUEST_BYTES: int = 1_048_576
    RATE_LIMIT_PER_MINUTE: int = 120
    RATE_LIMIT_BURST: int = 30

    DEBUG: bool = False
    SPORTS_DATA_PROVIDER: str = "mock"
    ODDS_PROVIDER: str = "mock"
    PERF_IMPORT_MOCK: bool = False

    AUTH_DEMO_EMAIL: str
    AUTH_DEMO_PASSWORD: str

    model_config = SettingsConfigDict(
        env_file=(str(ROOT_ENV_FILE), str(BACKEND_ENV_FILE)),
        extra="ignore",
    )

    @field_validator("SPORTSBOOK_API_KEYS", mode="before")
    @classmethod
    def parse_sportsbook_keys(cls, value: Any) -> dict[str, str]:
        if value in (None, ""):
            return {}
        if isinstance(value, dict):
            return {str(key): str(item) for key, item in value.items()}
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError as exc:
                raise ValueError("SPORTSBOOK_API_KEYS must be a JSON object") from exc
            if isinstance(parsed, dict):
                return {str(key): str(item) for key, item in parsed.items()}
        raise ValueError("SPORTSBOOK_API_KEYS must be a JSON object")

    @field_validator("SMTP_SETTINGS", mode="before")
    @classmethod
    def parse_smtp_settings(cls, value: Any) -> dict[str, Any]:
        if value in (None, ""):
            return {}
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError as exc:
                raise ValueError("SMTP_SETTINGS must be a JSON object") from exc
            if isinstance(parsed, dict):
                return parsed
        raise ValueError("SMTP_SETTINGS must be a JSON object")

    @property
    def JWT_SECRET_KEY(self) -> str:
        # Backward compatibility for existing imports.
        return self.JWT_SECRET

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]

    def resolved_odds_api_key(self) -> str:
        if self.ODDS_API_KEY:
            return self.ODDS_API_KEY
        return self.SPORTSBOOK_API_KEYS.get("odds_api", "")
