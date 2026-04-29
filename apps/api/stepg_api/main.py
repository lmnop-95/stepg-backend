import logging
from contextlib import asynccontextmanager
from importlib.metadata import version
from typing import TYPE_CHECKING

from fastapi import FastAPI
from pydantic import BaseModel
from stepg_core.core.logging import configure_logging
from stepg_core.features.extraction.anthropic_client import aclose_if_initialized

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
app.include_router(onboarding_router)


class HealthResponse(BaseModel):
    status: str


@app.get("/health")
async def health() -> HealthResponse:
    return HealthResponse(status="ok")
