from importlib.metadata import version

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="stepg-api", version=version("stepg-api"))


class HealthResponse(BaseModel):
    status: str


@app.get("/health")
async def health() -> HealthResponse:
    return HealthResponse(status="ok")
