from __future__ import annotations

from functools import lru_cache
import os

from settings.base import BaseAppSettings
from settings.development import DevelopmentSettings
from settings.production import ProductionSettings
from settings.staging import StagingSettings


@lru_cache(maxsize=1)
def get_settings() -> BaseAppSettings:
    env = (os.getenv("ENVIRONMENT") or os.getenv("APP_ENV") or "development").strip().lower()
    if env == "production":
        return ProductionSettings()
    if env == "staging":
        return StagingSettings()
    return DevelopmentSettings()
