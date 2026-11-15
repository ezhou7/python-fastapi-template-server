from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings. Environment variables override `.env`, which overrides the defaults."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://blog:blog@localhost:5432/blog"
    db_echo: bool = False


settings = Settings()
