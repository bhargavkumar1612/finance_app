from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://finances:finances_secret@localhost:5432/finances"
    redis_url: str = "redis://localhost:6379/0"
    gemini_api_key: str | None = None
    groq_api_key: str | None = None
    debug: bool = False
    log_level: str = "info"
    confidence_threshold: float = 0.6  # Default threshold for imports/ai

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def database_url_async(self) -> str:
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self.database_url

    @property
    def database_url_sync(self) -> str:
        return self.database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


settings = Settings()
