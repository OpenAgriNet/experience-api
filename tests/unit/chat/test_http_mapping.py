"""A validated `ChatRequest` becomes a `ChatTurn`: the same facts, no wire names."""

from typing import Any

from experience_api.chat.adapters.http.mapping import to_chat_turn
from experience_api.chat.adapters.http.schemas import ChatRequest
from experience_api.chat.domain import ChatTurn, Location, Message
from tests.support.examples import FOLLOW_UP as EXAMPLE


def test_the_contract_example_becomes_a_turn() -> None:
    turn = to_chat_turn(ChatRequest.model_validate(EXAMPLE))

    assert turn == ChatTurn(
        session_id="68a3872f-3f0d-4cf6-99a3-a350132a0080",
        message_id="1ab38d6c-6fdb-4849-8ea1-da5e80a8687c",
        query="And what about tomorrow?",
        history=(
            Message("user", "What is the weather today at my location?"),
            Message("assistant", "Nashik is clear today, 31°C, no rain expected."),
        ),
        source_language="en",
        target_language="en",
        location=Location(latitude=20.0059, longitude=73.7898),
    )


def test_no_location_stays_none() -> None:
    body: dict[str, Any] = {k: v for k, v in EXAMPLE.items() if k != "location"}

    assert to_chat_turn(ChatRequest.model_validate(body)).location is None
