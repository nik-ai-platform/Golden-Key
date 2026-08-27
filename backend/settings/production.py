from settings.base import BaseAppSettings


class ProductionSettings(BaseAppSettings):
    DEBUG: bool = False
    REQUEST_TIMEOUT_SECONDS: float = 15.0
    RATE_LIMIT_PER_MINUTE: int = 120
    MAX_REQUEST_BYTES: int = 786_432
