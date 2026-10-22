"""Rejected bodies get FastAPI's default 422 (contract §6.1, amended). Whatever
the body held, the rejection itself must be sendable."""

from collections.abc import AsyncGenerator

import httpx
import pytest
from fastapi import FastAPI

from experience_api.app import create_app
from experience_api.chat.adapters.dss.fake import FakeDssClient
from experience_api.chat.domain import ChatTurn, DssEvent
from tests.support.examples import FOLLOW_UP


class _SpyDss(FakeDssClient):
    """The fake DSS, counting the turns it gets. A rejected body must never
    reach it."""

    def __init__(self) -> None:
        super().__init__()
        self.turns: list[ChatTurn] = []

    async def stream_turn(
        self, turn: ChatTurn, *, transaction_id: str
    ) -> AsyncGenerator[DssEvent]:
        self.turns.append(turn)
        async for event in super().stream_turn(turn, transaction_id=transaction_id):
            yield event


@pytest.fixture
def spy() -> _SpyDss:
    return _SpyDss()


@pytest.fixture
def app(spy: _SpyDss) -> FastAPI:
    return create_app(dss=spy)


async def test_a_non_finite_coordinate_is_a_422_not_a_500(
    running: httpx.AsyncClient,
) -> None:
    # Python's JSON parser reads NaN and Infinity; strict JSON cannot write them
    # back, so a rejection that echoes the input must not echo them raw.
    for bad in ("NaN", "Infinity", "1e400"):
        body = FOLLOW_UP | {"location": "PLACEHOLDER"}
        raw = httpx.Request("POST", "/", json=body).content.decode()
        raw = raw.replace('"PLACEHOLDER"', f'{{"latitude": 20, "longitude": {bad}}}')

        response = await running.post(
            "/v1/chat", content=raw, headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422, bad
        assert response.json()["detail"][0]["loc"] == ["body", "location", "longitude"]


async def test_an_unknown_channel_is_a_422_and_never_reaches_the_dss(
    running: httpx.AsyncClient, spy: _SpyDss
) -> None:
    response = await running.post("/v1/chat", json=FOLLOW_UP | {"channel": "voice"})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "channel"]
    assert spy.turns == []


async def test_a_web_channel_reaches_the_dss(
    running: httpx.AsyncClient, spy: _SpyDss
) -> None:
    response = await running.post("/v1/chat", json=FOLLOW_UP | {"channel": "web"})

    assert response.status_code == 200
    assert [turn.channel for turn in spy.turns] == ["web"]
