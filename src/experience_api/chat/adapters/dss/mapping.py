"""Chat's domain to and from the DSS's wire shapes. Pure functions."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from pydantic import ValidationError

from experience_api.chat.adapters.dss import schemas
from experience_api.chat.adapters.dss.sse import Frame
from experience_api.chat.domain import (
    Answer,
    Block,
    ChatTurn,
    Citation,
    DssDelta,
    DssEvent,
    DssFinished,
    DssStarted,
    Message,
    Outcome,
    RefusalBlock,
    Source,
    TextBlock,
    TurnError,
)

logger = logging.getLogger(__name__)


class DssProtocolError(Exception):
    """The DSS sent a frame chat cannot read.

    Its message names the frame and which fields were wrong, never their values:
    the DSS's text can echo the user's words, and this message ends up in logs.
    """


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


# The DSS's event names (its `adapters/http/v1/sse.py`).
_CREATED = "turn.created"
_DELTA = "claim.delta"
_CLAIM = "claim.completed"
# `turn.failed` is not a broken stream: it ends an `unavailable` turn, a full
# answer with an error. Both terminal names become DssFinished (contract §7.1).
_TERMINAL = frozenset({"turn.completed", "turn.failed"})


def to_dss_events(frame: Frame) -> list[DssEvent]:
    """The chat events one DSS frame carries: none, one, or several.

    `claim.completed` carries nothing chat needs, since the terminal frame
    repeats every block with its citations. An event name we do not know is
    skipped and logged, so a new DSS event cannot break a turn.

    Raises `DssProtocolError` when a frame chat relies on is malformed.
    """

    if frame.event == _CLAIM:
        return []
    if frame.event not in {_CREATED, _DELTA, *_TERMINAL}:
        logger.warning("dss_event=%s skipped=unknown", frame.event)
        return []

    try:
        response = schemas.TurnResponse.model_validate_json(frame.data)
    except ValidationError as exc:
        # `from None`: the ValidationError's own message quotes the input.
        raise DssProtocolError(
            f"malformed {frame.event} frame: {_where(exc)}"
        ) from None
    if frame.event == _CREATED:
        return [
            DssStarted(
                assistant_message_id=response.context.res_message_id,
                trace_id=response.context.trace_id,
            )
        ]
    if frame.event == _DELTA:
        return [
            DssDelta(item.text)
            for item in response.message.content
            if item.type == "output_text_delta" and item.text is not None
        ]
    return [DssFinished(_answer(frame.event, response.message))]


def _where(exc: ValidationError) -> str:
    """Which fields failed and how, with no values."""

    return "; ".join(
        f"{'.'.join(str(part) for part in error['loc']) or 'body'} {error['type']}"
        for error in exc.errors(include_input=False, include_url=False)
    )


def _answer(event: str, message: schemas.ResponseMessage) -> Answer:
    if message.outcome is None:
        raise DssProtocolError(f"malformed {event} frame: message.outcome missing")
    error = message.error
    return Answer(
        outcome=Outcome(status=message.outcome.status, cause=message.outcome.cause),
        content=tuple(
            block for item in message.content if (block := _block(item)) is not None
        ),
        sources=tuple(Source(id=s.id, name=s.name, url=s.url) for s in message.sources),
        error=(
            TurnError(
                code=error.code,
                message=error.message,
                retryable=error.retryable,
                retry_after_seconds=error.retry_after_seconds,
            )
            if error
            else None
        ),
    )


def _block(item: schemas.ContentItem) -> Block | None:
    if item.text is None:
        return None
    if item.type == "refusal":
        return RefusalBlock(item.text)
    if item.type == "text":
        return TextBlock(
            item.text,
            citations=tuple(
                Citation(source_id=a.source_id, start=a.start_index, end=a.end_index)
                for a in item.annotations
                if a.type == "url_citation"
                and a.source_id is not None
                and a.start_index is not None
                and a.end_index is not None
            ),
        )
    logger.warning("dss_content_type=%s skipped=unknown", item.type)
    return None
