"""`HttpDssClient` against a local HTTP server playing the DSS."""

import json
from datetime import UTC, datetime

import pytest
from pytest_httpserver import HTTPServer
from werkzeug import Request

from experience_api.chat.adapters.dss.client import HttpDssClient
from experience_api.chat.adapters.dss.mapping import to_dss_request
from experience_api.chat.adapters.http.mapping import to_chat_turn
from experience_api.chat.adapters.http.schemas import ChatRequest
from experience_api.chat.domain import DssDelta, DssFinished, DssStarted
from tests.support import dss_streams
from tests.support.examples import FOLLOW_UP

TURN = to_chat_turn(ChatRequest.model_validate(FOLLOW_UP))
NOW = datetime(2026, 9, 23, 8, 0, tzinfo=UTC)


def _client(server: HTTPServer) -> HttpDssClient:
    return HttpDssClient(
        base_url=server.url_for(""),
        channel="web",
        max_characters=1200,
        clock=lambda: NOW,
    )


def _serve(server: HTTPServer, stream: bytes) -> None:
    server.expect_request("/v1/turns", method="POST").respond_with_data(
        stream, content_type="text/event-stream"
    )


async def test_streams_a_turn(httpserver: HTTPServer) -> None:
    _serve(httpserver, dss_streams.ANSWERED)

    async with _client(httpserver) as dss:
        events = [e async for e in dss.stream_turn(TURN, transaction_id="tx-1")]

    assert isinstance(events[0], DssStarted)
    assert events[1:3] == [DssDelta("Light rain "), DssDelta("after 3 pm.")]
    assert isinstance(events[3], DssFinished)
    assert len(events) == 4


async def test_sends_the_contract_request(httpserver: HTTPServer) -> None:
    _serve(httpserver, dss_streams.NO_MATCH)

    async with _client(httpserver) as dss:
        [e async for e in dss.stream_turn(TURN, transaction_id="tx-1")]

    (request, _), *_ = httpserver.log
    assert isinstance(request, Request)
    assert request.headers["Accept"] == "text/event-stream"
    assert request.headers["Content-Type"] == "application/json"
    assert json.loads(request.get_data()) == to_dss_request(
        TURN, transaction_id="tx-1", now=NOW, channel="web", max_characters=1200
    )


async def test_the_connection_pool_closes_with_the_client(
    httpserver: HTTPServer,
) -> None:
    async with _client(httpserver) as dss:
        pass

    with pytest.raises(RuntimeError, match="closed"):
        [e async for e in dss.stream_turn(TURN, transaction_id="tx-1")]
