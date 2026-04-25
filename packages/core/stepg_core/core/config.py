from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ASYNC_DRIVER_PREFIXES = ("postgresql+asyncpg://", "postgresql+psycopg://")
_REDIS_DSN_PREFIXES = ("redis://", "rediss://")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="forbid",
        frozen=True,
    )

    app_env: Literal["development", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    frontend_url: str | None = None
    cookie_domain: str | None = None
    cors_origins: list[str] = Field(default_factory=list)

    nextauth_secret: SecretStr | None = None

    database_url: SecretStr
    redis_url: SecretStr

    anthropic_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None
    clova_ocr_url: str | None = None
    clova_ocr_secret: SecretStr | None = None

    bizinfo_api_key: SecretStr | None = None
    data_go_kr_service_key: SecretStr | None = None
    kstartup_api_key: SecretStr | None = None

    resend_api_key: SecretStr | None = None
    resend_from_email: str | None = None

    sentry_dsn_backend: SecretStr | None = None
    sentry_dsn_worker: SecretStr | None = None
    logfire_token: SecretStr | None = None

    @field_validator("database_url")
    @classmethod
    def _require_async_driver(cls, v: SecretStr) -> SecretStr:
        if not v.get_secret_value().startswith(_ASYNC_DRIVER_PREFIXES):
            raise ValueError(
                "DATABASE_URL은 async 드라이버여야 합니다 "
                f"(허용 prefix: {', '.join(_ASYNC_DRIVER_PREFIXES)})"
            )
        return v

    @field_validator("redis_url")
    @classmethod
    def _require_redis_scheme(cls, v: SecretStr) -> SecretStr:
        if not v.get_secret_value().startswith(_REDIS_DSN_PREFIXES):
            raise ValueError(
                "REDIS_URL은 redis:// 또는 rediss:// 스킴이어야 합니다 "
                f"(허용 prefix: {', '.join(_REDIS_DSN_PREFIXES)})"
            )
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]
