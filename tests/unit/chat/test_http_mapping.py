"""A validated `ChatRequest` becomes a `ChatTurn`: the same facts, no wire names."""

from typing import Any

from experience_api.chat.adapters.http.mapping import to_chat_turn
from experience_api.chat.adapters.http.schemas import ChatRequest
from experience_api.chat.domain import Channel
from tests.support.examples import FOLLOW_UP as EXAMPLE
from tests.support.examples import FOLLOW_UP_TURN


def test_the_contract_example_becomes_a_turn() -> None:
    turn = to_chat_turn(
        ChatRequest.model_validate(EXAMPLE), default_channel=Channel.WEB
    )

    assert turn == FOLLOW_UP_TURN


def test_no_location_stays_none() -> None:
    body: dict[str, Any] = {k: v for k, v in EXAMPLE.items() if k != "location"}

    assert (
        to_chat_turn(
            ChatRequest.model_validate(body), default_channel=Channel.WEB
        ).location
        is None
    )


def test_ids_pass_through_exactly_as_sent() -> None:
    body = EXAMPLE | {
        "sessionId": "68A3872F-3F0D-4CF6-99A3-A350132A0080",
        "messageId": "1AB38D6C-6fdb-4849-8ea1-da5e80a8687c",
    }

    turn = to_chat_turn(ChatRequest.model_validate(body), default_channel=Channel.WEB)

    assert turn.session_id == "68A3872F-3F0D-4CF6-99A3-A350132A0080"
    assert turn.message_id == "1AB38D6C-6fdb-4849-8ea1-da5e80a8687c"


def test_a_sent_channel_is_used() -> None:
    body = EXAMPLE | {"channel": "web"}

    turn = to_chat_turn(ChatRequest.model_validate(body), default_channel=Channel.WEB)

    assert turn.channel is Channel.WEB


def test_no_channel_takes_the_default() -> None:
    turn = to_chat_turn(
        ChatRequest.model_validate(EXAMPLE), default_channel=Channel.WEB
    )

    assert turn.channel is Channel.WEB
