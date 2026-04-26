from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ASYNC_DRIVER_PREFIXES = ("postgresql+asyncpg://", "postgresql+psycopg://")
_REDIS_DSN_PREFIXES = ("redis://", "rediss://")
_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_STORAGE_ROOT = _REPO_ROOT / "storage"


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

    storage_root: Path = Field(default=_DEFAULT_STORAGE_ROOT)

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

    @field_validator("storage_root", mode="after")
    @classmethod
    def _resolve_storage_root(cls, v: Path) -> Path:
        # apps/api와 apps/worker가 다른 cwd에서 실행돼도 같은 storage 가리키도록
        # 절대경로 강제. `~/storage` 같은 dev 머신 패턴은 expanduser로 흡수.
        resolved = v.expanduser()
        if not resolved.is_absolute():
            raise ValueError(
                f"STORAGE_ROOT는 절대경로여야 합니다 (입력: {v}, expanduser 후: {resolved})"
            )
        return resolved


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]
