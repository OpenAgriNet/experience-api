"""`POST /v1/chat` with `Accept: text/event-stream` (contract §5.1).

Frames are compared byte for byte, so raw UTF-8 (`°C`) and the `sequence`
counter are both pinned.
"""

import json

import httpx
import pytest
from fastapi import FastAPI

from experience_api.app import create_app
from experience_api.chat.adapters.dss.fake import FakeDssClient
from tests.support.examples import ANSWERED, FAKE_ANSWERED, FAKE_PIECES, FOLLOW_UP

SSE = {"Accept": "text/event-stream"}


@pytest.fixture
def app() -> FastAPI:
    return create_app(
        dss=FakeDssClient(new_id=lambda: ANSWERED["assistantMessageId"]),
        new_id=lambda: ANSWERED["traceId"],
    )


def _frame(event: str, data: dict[str, object]) -> str:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {payload}\n\n"


async def test_streams_the_fake_answer_frame_by_frame(
    running: httpx.AsyncClient,
) -> None:
    response = await running.post("/v1/chat", json=FOLLOW_UP, headers=SSE)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    ids = {k: ANSWERED[k] for k in ("sessionId", "messageId", "assistantMessageId")}
    pieces = [
        _frame("delta", {"sequence": n, "text": text})
        for n, text in enumerate(FAKE_PIECES, start=2)
    ]
    last = len(FAKE_PIECES) + 2
    assert response.text == "".join(
        [
            _frame("started", {"sequence": 1, **ids, "traceId": ANSWERED["traceId"]}),
            *pieces,
            _frame("completed", {"sequence": last, **FAKE_ANSWERED}),
        ]
    )


async def test_a_body_that_breaks_the_contract_is_a_422(
    running: httpx.AsyncClient,
) -> None:
    response = await running.post(
        "/v1/chat", json={**FOLLOW_UP, "query": " "}, headers=SSE
    )

    assert response.status_code == 422


async def test_asks_proxies_and_caches_not_to_hold_the_stream(
    running: httpx.AsyncClient,
) -> None:
    response = await running.post("/v1/chat", json=FOLLOW_UP, headers=SSE)

    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["x-accel-buffering"] == "no"
