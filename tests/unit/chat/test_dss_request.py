"""A ChatTurn becomes the DSS's `/v1/turns` request (contract §7)."""

from dataclasses import replace
from datetime import UTC, datetime

from experience_api.chat.adapters.dss.mapping import to_dss_request
from experience_api.chat.domain import Channel, Message
from tests.support.examples import (
    DSS_REQUEST,
    FOLLOW_UP_TURN,
    FORM_CONTEXT,
    FORM_SENT_TURN,
    SENDER_ID,
)

TURN = FOLLOW_UP_TURN
NOW = datetime(2026, 9, 23, 8, 0, tzinfo=UTC)


def _request(turn=TURN) -> dict:  # noqa: ANN001
    return to_dss_request(
        turn,
        transaction_id="3c67dc05-6ba2-4ab4-bb7c-377e16a5ab5b",
        now=NOW,
        sender_id=SENDER_ID,
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


def test_the_channel_comes_from_the_turn() -> None:
    attributes = _request(replace(TURN, channel=Channel.WEB))["message"]["attributes"]

    assert attributes["channel"] == "web"


def test_a_sent_form_is_the_last_user_message() -> None:
    turn = replace(
        FORM_SENT_TURN,
        history=(
            Message("user", "I want to file a PMFBY grievance"),
            Message("assistant", "Please fill in this form."),
        ),
    )

    inputs = _request(turn)["message"]["input"]

    assert inputs[:2] == [
        {
            "role": "user",
            "content": [{"type": "text", "text": "I want to file a PMFBY grievance"}],
        },
        {
            "role": "assistant",
            "content": [{"type": "text", "text": "Please fill in this form."}],
        },
    ]
    assert inputs[2] == {
        "role": "user",
        "content": [
            {
                "type": "form",
                "formId": "f-1",
                "context": FORM_CONTEXT,
                "submissionId": "9e8d7c6b-5a4f-4e3d-8c2b-1a0f9e8d7c6b",
                "fields": [
                    {"name": "applicantPhone", "value": "9876543210"},
                    # An optional field left blank still goes: the DSS reads
                    # blank as not given.
                    {"name": "season", "value": ""},
                ],
            }
        ],
    }
