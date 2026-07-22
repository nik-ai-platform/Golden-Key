from pathlib import Path

from pydantic_settings import BaseSettings


ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    APP_NAME: str = "Nik AI Sports Betting Platform"
    VERSION: str = "1.0.0"

    DATABASE_URL: str = (
        "postgresql://postgres:postgres@localhost:5432/nikai"
    )

    DEBUG: bool = True

    # Provider selection defaults to local mock implementations.
    SPORTS_DATA_PROVIDER: str = "mock"
    ODDS_PROVIDER: str = "mock"

    ODDS_API_KEY: str
    ODDS_API_BASE_URL: str = "https://api.the-odds-api.com/v4"

    class Config:
        env_file = str(ENV_FILE)


settings = Settings()
