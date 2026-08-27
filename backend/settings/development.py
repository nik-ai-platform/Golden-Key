from settings.base import BaseAppSettings


class DevelopmentSettings(BaseAppSettings):
    DEBUG: bool = True
    REQUEST_TIMEOUT_SECONDS: float = 30.0
    RATE_LIMIT_PER_MINUTE: int = 240
