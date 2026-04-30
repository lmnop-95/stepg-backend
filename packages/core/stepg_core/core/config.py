from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ASYNC_DRIVER_PREFIXES = ("postgresql+asyncpg://", "postgresql+psycopg://")
_REDIS_DSN_PREFIXES = ("redis://", "rediss://")
REPO_ROOT = Path(__file__).resolve().parents[4]
"""Repository root (editable workspace install 가정 — `parents[4]`가 backend repo
root). 비-editable 설치(`pip install stepg-core`)에서는 `parents[4]`가 site-packages
임의 경로가 되므로 의존하면 안 됨; 그런 경우 `Settings.storage_root` 같은 명시 path를
운영자가 박는다 (`_require_explicit_storage_root_in_prod` validator). M4 features/extraction
모듈이 `docs/TAXONOMY.md` lazy load 시 본 상수를 import — `parents[N]` 두 곳 dual SoT
회피."""
_DEFAULT_STORAGE_ROOT = REPO_ROOT / "storage"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="forbid",
        frozen=True,
        env_ignore_empty=True,
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

    pdf_ocr_fallback_min_chars_per_page: int = Field(
        default=50,
        ge=0,
        description="페이지 추출 글자수 < 임계 시 OCR fallback. 0 = OCR 비활성화 (dev escape hatch).",
    )

    anthropic_api_key: SecretStr | None = None
    anthropic_model: str = Field(
        default="claude-sonnet-4-6",
        description="Anthropic model ID for M4 extraction. Staging/prod 검증 시 모델 교체 가능.",
    )
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

    @model_validator(mode="after")
    def _require_explicit_storage_root_in_prod(self) -> Settings:
        # `_DEFAULT_STORAGE_ROOT` (`<repo-root>/storage`)는 editable workspace 설치
        # 가정 — 비-editable 설치(`pip install stepg-core`로 site-packages 실행) 시
        # `parents[4]`가 임의 경로가 됨. staging/production에서는 attachments 적재
        # 위치가 운영자 의도대로여야 하므로 STORAGE_ROOT 명시 강제 (CodeRabbit
        # #3145455681). dev에선 default OK.
        if (
            self.app_env in ("staging", "production")
            and "storage_root" not in self.model_fields_set
        ):
            raise ValueError(
                f"STORAGE_ROOT는 app_env={self.app_env}에서 반드시 명시해야 합니다 "
                "— `_DEFAULT_STORAGE_ROOT`(parents[4] 기반)는 editable install 가정"
            )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]


__all__ = ["REPO_ROOT", "Settings", "get_settings"]
