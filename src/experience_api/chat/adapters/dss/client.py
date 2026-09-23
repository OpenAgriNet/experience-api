"""HttpDssClient: one turn at a time over the DSS's `POST /v1/turns`.

It always asks for the event stream, even for a JSON client, whose route drains
it (contract §7). It holds one `httpx.AsyncClient`, a connection pool shared by
every turn, so it is an async context manager: whoever builds it enters it, and
leaving closes the pool.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable
from datetime import UTC, datetime
from typing import Self

import httpx

from experience_api.chat.adapters.dss import sse
from experience_api.chat.adapters.dss.mapping import to_dss_events, to_dss_request
from experience_api.chat.domain import ChatTurn, DssEvent

_SSE = "text/event-stream"

# A safety net until the turn's own timers arrive: a DSS that never answers
# cannot hold a request forever. Reading allows the whole-turn limit between
# chunks, since the DSS sends no keep-alives and may be quiet while it works.
_TIMEOUT = httpx.Timeout(connect=5.0, read=120.0, write=10.0, pool=5.0)


class HttpDssClient:
    def __init__(
        self,
        *,
        base_url: str,
        channel: str,
        max_characters: int,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._http = httpx.AsyncClient(base_url=base_url, timeout=_TIMEOUT)
        self._channel = channel
        self._max_characters = max_characters
        self._clock = clock

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self._http.aclose()

    async def stream_turn(
        self, turn: ChatTurn, *, transaction_id: str
    ) -> AsyncGenerator[DssEvent]:
        body = to_dss_request(
            turn,
            transaction_id=transaction_id,
            now=self._clock(),
            channel=self._channel,
            max_characters=self._max_characters,
        )
        # Leaving this block, including when the reader stops early, closes the
        # response, which drops the connection and ends the DSS's turn.
        async with self._http.stream(
            "POST", "/v1/turns", json=body, headers={"Accept": _SSE}
        ) as response:
            # Until DSS statuses are mapped to chat errors, any non-2xx fails.
            response.raise_for_status()
            async for frame in sse.parse(response.aiter_bytes()):
                for event in to_dss_events(frame):
                    yield event
