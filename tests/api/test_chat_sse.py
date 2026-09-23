"""`POST /v1/chat` with `Accept: text/event-stream` (contract §5.1)."""

import json

import httpx
import pytest
from fastapi import FastAPI

from experience_api.app import create_app
from experience_api.chat.adapters.dss.fake import FakeDssClient
from tests.support.examples import ANSWERED, FOLLOW_UP

SSE = {"Accept": "text/event-stream"}


@pytest.fixture
def app() -> FastAPI:
    return create_app(
        dss=FakeDssClient(new_id=lambda: ANSWERED["assistantMessageId"]),
        new_id=lambda: ANSWERED["traceId"],
    )


def _frame(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"


async def test_streams_the_contract_example(running: httpx.AsyncClient) -> None:
    response = await running.post("/v1/chat", json=FOLLOW_UP, headers=SSE)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    ids = {k: ANSWERED[k] for k in ("sessionId", "messageId", "assistantMessageId")}
    assert response.text == "".join(
        [
            _frame("started", {"sequence": 1, **ids, "traceId": ANSWERED["traceId"]}),
            _frame("delta", {"sequence": 2, "text": "Tomorrow in Nashik "}),
            _frame("delta", {"sequence": 3, "text": "expect light rain after 3 pm."}),
            _frame("completed", {"sequence": 4, **ANSWERED}),
        ]
    )


async def test_a_body_that_breaks_the_contract_is_a_422(
    running: httpx.AsyncClient,
) -> None:
    response = await running.post(
        "/v1/chat", json={**FOLLOW_UP, "query": " "}, headers=SSE
    )

    assert response.status_code == 422
