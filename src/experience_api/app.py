"""The composition root: `create_app()` builds the FastAPI app.

`uvicorn --factory` calls it with no arguments, so it must boot with nothing
configured. Objects the app needs for its whole life, such as an HTTP client
pool, are built in `lifespan`; none exist yet.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield

    return FastAPI(title="Experience API", lifespan=lifespan)
