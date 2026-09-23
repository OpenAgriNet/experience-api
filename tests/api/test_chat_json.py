"""`POST /v1/chat` without `Accept: text/event-stream` (contract §5.2).

The API streams from the DSS either way; JSON mode drains the stream into one
FinalAnswer.
"""

import httpx
import pytest
from fastapi import FastAPI

from experience_api.app import create_app
from experience_api.chat.adapters.dss.fake import FakeDssClient
from tests.support.examples import ANSWERED, FAKE_ANSWERED, FOLLOW_UP


@pytest.fixture
def app() -> FastAPI:
    return create_app(
        dss=FakeDssClient(new_id=lambda: ANSWERED["assistantMessageId"]),
        new_id=lambda: ANSWERED["traceId"],
    )


@pytest.mark.parametrize(
    "accept",
    [
        None,
        "application/json",
        "*/*",
        "text/html",
        "text/event-stream;q=0",
        "application/json, text/event-stream; q=0.0",
    ],
    ids=[
        "absent",
        "json",
        "anything",
        "neither",
        "sse refused",
        "sse refused among others",
    ],
)
async def test_answers_with_one_final_answer(
    running: httpx.AsyncClient, accept: str | None
) -> None:
    headers = {"Accept": accept} if accept else {}
    if accept is None:
        # httpx sends `Accept: */*` unless told otherwise.
        running.headers.pop("Accept", None)

    response = await running.post("/v1/chat", json=FOLLOW_UP, headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == FAKE_ANSWERED


@pytest.mark.parametrize(
    "accept",
    [
        "text/event-stream",
        "application/json, text/event-stream;q=0.9",
        "TEXT/Event-Stream",
        " text/event-stream ; q=1 ",
        "text/event-stream;q=nonsense",
    ],
    ids=["sse", "sse among others", "any case", "spaces", "unreadable q"],
)
async def test_any_mention_of_the_event_stream_streams(
    running: httpx.AsyncClient, accept: str
) -> None:
    response = await running.post(
        "/v1/chat", json=FOLLOW_UP, headers={"Accept": accept}
    )

    assert response.headers["content-type"].startswith("text/event-stream")


async def test_the_openapi_document_describes_both_answers(
    running: httpx.AsyncClient,
) -> None:
    ok = (await running.get("/openapi.json")).json()["paths"]["/v1/chat"]["post"][
        "responses"
    ]["200"]["content"]

    assert set(ok) == {"application/json", "text/event-stream"}
    assert ok["application/json"]["schema"] == {
        "$ref": "#/components/schemas/FinalAnswer"
    }
