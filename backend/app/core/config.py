from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Nik AI Sports Betting Platform"
    VERSION: str = "1.0.0"

    DATABASE_URL: str = (
        "postgresql://postgres:postgres@localhost:5432/nikai"
    )

    DEBUG: bool = True

    class Config:
        env_file = ".env"


settings = Settings()
