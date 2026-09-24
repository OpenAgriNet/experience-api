"""The composition root: `create_app()` builds the FastAPI app.

It is the one place that knows which concrete objects exist. Objects the app
needs for its whole life are built in `lifespan` and kept on `app.state`. It is
also the only reader of settings: services get plain values.

`uvicorn --factory` calls it with no arguments, so it must boot with nothing
configured: it reads `Settings` from the environment. Tests pass their own
settings, DSS and id factory.

`/healthz` lives here because it belongs to the running service, not to any
feature.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import AsyncExitStack, asynccontextmanager
from uuid import uuid4

from fastapi import APIRouter, FastAPI

from experience_api.chat.adapters.dss.client import HttpDssClient
from experience_api.chat.adapters.dss.fake import FakeDssClient
from experience_api.chat.adapters.http.routes import router as chat_router
from experience_api.chat.ports import DssClient
from experience_api.chat.service import ChatService
from experience_api.settings import Settings
from experience_api.shared import errors

health = APIRouter()


@health.get("/healthz", include_in_schema=False)
async def healthz() -> dict[str, str]:
    """For Docker and the front proxy. Says the process is up and serving. It
    does not probe the DSS, so a DSS outage never takes the API out of rotation
    with it."""

    return {"status": "ok"}


def create_app(
    settings: Settings | None = None,
    *,
    dss: DssClient | None = None,
    new_id: Callable[[], str] = lambda: str(uuid4()),
) -> FastAPI:
    settings = settings if settings is not None else Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Whoever builds a client closes it: the stack closes what this builds,
        # and a test that passes a client in owns it.
        async with AsyncExitStack() as stack:
            client = dss if dss is not None else await _dss_client(settings, stack)
            app.state.chat_service = ChatService(client, new_id=new_id)
            yield

    app = FastAPI(title="Experience API", lifespan=lifespan)
    errors.register(app)
    app.include_router(health)
    app.include_router(chat_router, prefix="/v1")
    return app


async def _dss_client(settings: Settings, stack: AsyncExitStack) -> DssClient:
    if settings.dss_mode == "fake":
        return FakeDssClient()
    return await stack.enter_async_context(
        HttpDssClient(
            base_url=settings.dss_base_url,
            channel=settings.channel,
            max_characters=settings.max_characters,
        )
    )
