from contextlib import asynccontextmanager
from importlib.metadata import version
from typing import TYPE_CHECKING

from fastapi import FastAPI
from pydantic import BaseModel
from stepg_core.core.logging import configure_logging

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    configure_logging()
    yield


app = FastAPI(title="stepg-api", version=version("stepg-api"), lifespan=lifespan)


class HealthResponse(BaseModel):
    status: str


@app.get("/health")
async def health() -> HealthResponse:
    return HealthResponse(status="ok")
