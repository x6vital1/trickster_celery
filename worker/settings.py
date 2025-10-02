import os
from functools import lru_cache
from urllib.parse import quote
from loguru import logger
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = 'development'
    REDIS_HOST: str = 'localhost'
    REDIS_PORT: int = 6379
    REDIS_USER: str | None = None
    REDIS_PASS: str | None = None
    REDIS_SSL: bool = False
    REDIS_DB_BROKER: int = 0
    REDIS_DB_BACKEND: int = 1

    API_BASE: str = 'https://api.trickster-shop.cloud'
    EMAIL_API_KEY: str
    EMAIL_API_KEY_HEADER: str = 'api-key'

    ALLOCATE_PAUSE_SEC: float = 0.3
    MAIL_WAIT_TIMEOUT_SEC: int = 90
    POLL_INTERVAL_SEC: float = 10
    MESSAGE_TTL_SEC: int = 259200

    EMAIL_API_VERIFY_TLS: bool = True
    EMAIL_API_ALLOCATE_TIMEOUT: int = 30
    EMAIL_API_MESSAGES_TIMEOUT: int = 15

    @property
    def REDIS_URL(self) -> str:
        user = quote(self.REDIS_USER) if self.REDIS_USER else ""
        pw = f":{quote(self.REDIS_PASS)}" if self.REDIS_PASS else ""
        auth = f"{user}{pw}@" if (user or pw) else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'),
        env_file_encoding='utf-8',
        extra='ignore'
    )


@lru_cache
def get_settings() -> Settings:
    logger.info(f"Initializing settings for ENVIRONMENT='{os.getenv('ENVIRONMENT', 'development')}'")
    return Settings()


settings = get_settings()
