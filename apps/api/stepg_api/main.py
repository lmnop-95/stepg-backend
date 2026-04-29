import logging
from contextlib import asynccontextmanager
from importlib.metadata import version
from typing import TYPE_CHECKING

from fastapi import Depends, FastAPI
from pydantic import BaseModel
from stepg_core.core.logging import configure_logging
from stepg_core.features.extraction.anthropic_client import aclose_if_initialized

from stepg_api.auth.deps import get_current_user_id
from stepg_api.routes.onboarding import router as onboarding_router

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    configure_logging()
    yield
    await aclose_if_initialized(logger)


app = FastAPI(title="stepg-api", version=version("stepg-api"), lifespan=lifespan)
# Q61 — `/onboarding/*` router-level dependency: `/ocr` 도 보호 (CLOVA 비용
# abuse 차단). `/complete` 의 path-level `Depends(get_current_user_id)` 는
# user_id 값 사용 위해 유지 — FastAPI 가 같은 sub-dep 캐시하므로 추가 비용 X.
app.include_router(onboarding_router, dependencies=[Depends(get_current_user_id)])


class HealthResponse(BaseModel):
    status: str


@app.get("/health")
async def health() -> HealthResponse:
    return HealthResponse(status="ok")
