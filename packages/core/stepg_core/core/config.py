from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ASYNC_DRIVER_PREFIXES = ("postgresql+asyncpg://", "postgresql+psycopg://")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["development", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    database_url: SecretStr
    redis_url: SecretStr

    @field_validator("database_url")
    @classmethod
    def _require_async_driver(cls, v: SecretStr) -> SecretStr:
        if not v.get_secret_value().startswith(_ASYNC_DRIVER_PREFIXES):
            raise ValueError(
                "DATABASE_URL은 async 드라이버여야 합니다 "
                f"(허용 prefix: {', '.join(_ASYNC_DRIVER_PREFIXES)})"
            )
        return v


settings = Settings()  # pyright: ignore[reportCallIssue]
