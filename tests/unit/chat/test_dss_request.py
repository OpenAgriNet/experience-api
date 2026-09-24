"""A ChatTurn becomes the DSS's `/v1/turns` request (contract §7)."""

from dataclasses import replace
from datetime import UTC, datetime

from experience_api.chat.adapters.dss.mapping import to_dss_request
from experience_api.chat.adapters.http.mapping import to_chat_turn
from experience_api.chat.adapters.http.schemas import ChatRequest
from tests.support.examples import DSS_REQUEST, FOLLOW_UP

TURN = to_chat_turn(ChatRequest.model_validate(FOLLOW_UP))
NOW = datetime(2026, 9, 23, 8, 0, tzinfo=UTC)


def _request(turn=TURN) -> dict:  # noqa: ANN001
    return to_dss_request(
        turn,
        transaction_id="3c67dc05-6ba2-4ab4-bb7c-377e16a5ab5b",
        now=NOW,
        channel="web",
        max_characters=1200,
    )


def test_the_contract_example() -> None:
    assert _request() == DSS_REQUEST


def test_coordinates_go_longitude_first() -> None:
    geometry = _request()["message"]["attributes"]["location"]["geometry"]

    # GeoJSON order. Both numbers are valid as either axis, so only a test
    # catches a swap.
    assert geometry["coordinates"] == [TURN.location.longitude, TURN.location.latitude]  # type: ignore[union-attr]


def test_no_location_leaves_the_attribute_out() -> None:
    attributes = _request(replace(TURN, location=None))["message"]["attributes"]

    assert "location" not in attributes


def test_a_first_message_is_the_only_input() -> None:
    inputs = _request(replace(TURN, history=()))["message"]["input"]

    assert inputs == [
        {"role": "user", "content": [{"type": "text", "text": TURN.query}]}
    ]
