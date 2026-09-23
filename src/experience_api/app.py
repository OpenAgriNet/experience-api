"""The composition root: `create_app()` builds the FastAPI app.

`uvicorn --factory` calls it with no arguments, so it must boot with nothing
configured. Objects the app needs for its whole life, such as an HTTP client
pool, are built in `lifespan`; none exist yet.

`/healthz` lives here because it belongs to the running service, not to any
feature.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

health = APIRouter()


@health.get("/healthz", include_in_schema=False)
async def healthz() -> dict[str, str]:
    """For Docker and the front proxy. Says the process is up and serving. It
    does not probe the DSS, so a DSS outage never takes the API out of rotation
    with it."""

    return {"status": "ok"}


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield

    app = FastAPI(title="Experience API", lifespan=lifespan)
    app.include_router(health)
    return app
