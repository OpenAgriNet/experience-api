"""Chat's domain to and from the DSS's wire shapes. Pure functions."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from experience_api.chat.adapters.dss import schemas
from experience_api.chat.domain import ChatTurn, Message

# Until sign-in exists (contract §8.2 item 3).
ANONYMOUS = "anonymous"


def to_dss_request(
    turn: ChatTurn,
    *,
    transaction_id: str,
    now: datetime,
    channel: str,
    max_characters: int,
) -> dict[str, Any]:
    """The `/v1/turns` body for one turn, contract §7.

    `now` is the API's clock, not the browser's. The history goes first, then
    the query as the last `user` message, so the DSS finds the question where
    it looks for it.
    """

    location = turn.location
    request = schemas.TurnRequest(
        context=schemas.Context(
            timestamp=now,
            session_id=turn.session_id,
            transaction_id=transaction_id,
            message_id=turn.message_id,
        ),
        message=schemas.Message(
            input=[
                _input(message)
                for message in (*turn.history, Message("user", turn.query))
            ],
            attributes=schemas.Attributes(
                channel=channel,
                source_language=turn.source_language,
                target_language=turn.target_language,
                location=(
                    schemas.Location(
                        geometry=schemas.Geometry(
                            coordinates=(location.longitude, location.latitude)
                        )
                    )
                    if location
                    else None
                ),
                response=schemas.ResponseSpec(max_characters=max_characters),
            ),
            user_context=[schemas.Identity(user_id=ANONYMOUS)],
        ),
    )
    return schemas.wire(request)


def _input(message: Message) -> schemas.InputMessage:
    return schemas.InputMessage(
        role=message.role, content=[schemas.TextPart(text=message.text)]
    )
