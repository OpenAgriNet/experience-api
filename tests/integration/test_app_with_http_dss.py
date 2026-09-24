"""The whole API in http mode: a client's turn, through the real DSS client, to
a local server playing the DSS, and back."""

import httpx
import pytest
from fastapi import FastAPI
from pytest_httpserver import HTTPServer

from experience_api.app import create_app
from experience_api.settings import Settings
from tests.support import dss_streams
from tests.support.examples import FOLLOW_UP


@pytest.fixture
def app(httpserver: HTTPServer) -> FastAPI:
    httpserver.expect_request("/v1/turns", method="POST").respond_with_data(
        dss_streams.ANSWERED, content_type="text/event-stream"
    )
    return create_app(Settings(dss_mode="http", dss_base_url=httpserver.url_for("")))


async def test_a_streamed_turn(running: httpx.AsyncClient) -> None:
    response = await running.post(
        "/v1/chat", json=FOLLOW_UP, headers={"Accept": "text/event-stream"}
    )

    events = [
        line[7:] for line in response.text.splitlines() if line.startswith("event: ")
    ]
    assert events == ["started", "delta", "delta", "completed"]
    assert '"text":"Light rain "' in response.text


async def test_a_json_turn(running: httpx.AsyncClient) -> None:
    body = (await running.post("/v1/chat", json=FOLLOW_UP)).json()

    assert body["outcome"] == {"status": "partially_answered", "cause": "out_of_scope"}
    assert [c["type"] for c in body["content"]] == ["text", "refusal"]
    assert body["assistantMessageId"] == dss_streams.CONTEXT["resMessageId"]
    assert body["traceId"] == dss_streams.CONTEXT["traceId"]
