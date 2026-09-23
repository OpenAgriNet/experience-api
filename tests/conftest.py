"""Fixtures shared by every tier."""

from collections.abc import AsyncIterator

import httpx
import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI

from experience_api.app import create_app


@pytest.fixture
def app() -> FastAPI:
    """The app as `uvicorn --factory` builds it. A module that needs different
    wiring overrides this fixture with its own `create_app(...)` call."""

    return create_app()


@pytest.fixture
async def running(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    """The app with its lifespan started, behind an in-process HTTP client.

    httpx's ASGI transport does not run lifespan events, and everything the app
    needs is built there, so a test that skips it would hit an empty `app.state`.
    """

    async with (
        LifespanManager(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client,
    ):
        yield client
