"""Fixtures shared by every tier."""

from collections.abc import AsyncIterator

import httpx
import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI

from experience_api.app import create_app
from experience_api.settings import Settings
from tests.support.examples import SENDER_ID


@pytest.fixture(autouse=True)
def _settings_from_the_test_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests never read a developer's `.env`: it could point them at a real DSS.
    Every test runs as the contract's example sender. A test that needs `.env`
    points `env_file` at its own file the same way."""

    monkeypatch.setitem(Settings.model_config, "env_file", None)
    monkeypatch.setenv("EXPERIENCE_API_SENDER_ID", SENDER_ID)


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
