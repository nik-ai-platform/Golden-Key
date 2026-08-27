from settings.base import BaseAppSettings


class StagingSettings(BaseAppSettings):
    DEBUG: bool = False
    REQUEST_TIMEOUT_SECONDS: float = 20.0
    RATE_LIMIT_PER_MINUTE: int = 180
