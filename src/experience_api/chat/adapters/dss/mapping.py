"""Chat's domain to and from the DSS's wire shapes. Pure functions."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from pydantic import ValidationError

from experience_api.chat.adapters.dss import schemas
from experience_api.chat.domain import (
    Answer,
    Block,
    ChatTurn,
    Citation,
    DssDelta,
    DssEvent,
    DssFinished,
    DssStarted,
    FieldError,
    FormBlock,
    FormErrorBlock,
    FormField,
    FormOption,
    FormSubmission,
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
    sender_id: str,
    max_characters: int,
) -> dict[str, Any]:
    """The `/v1/turns` body for one turn, contract §7.

    `now` is the API's clock, not the browser's. The history goes first, then
    the query, a question or a filled form, as the last `user` message, so the
    DSS finds it where it looks for it.
    """

    location = turn.location
    request = schemas.TurnRequest(
        context=schemas.Context(
            timestamp=now,
            session_id=turn.session_id,
            transaction_id=transaction_id,
            message_id=turn.message_id,
            sender_id=sender_id,
        ),
        message=schemas.Message(
            input=[*(_input(message) for message in turn.history), _query(turn.query)],
            attributes=schemas.Attributes(
                channel=turn.channel,
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


def _query(query: str | FormSubmission) -> schemas.InputMessage:
    if isinstance(query, str):
        return _input(Message("user", query))
    return schemas.InputMessage(
        role="user",
        content=[
            schemas.FormPart(
                form_id=query.form_id,
                context=dict(query.context),
                submission_id=query.submission_id,
                fields=[
                    schemas.SubmittedField(name=v.name, value=v.value)
                    for v in query.values
                ],
            )
        ],
    )


# The DSS's event names (its `adapters/http/v1/sse.py`).
_CREATED = "turn.created"
_DELTA = "claim.delta"
_CLAIM = "claim.completed"
# `turn.failed` is not a broken stream: it ends an `unavailable` turn, a full
# answer with an error. Both terminal names become DssFinished (contract §7.1).
_TERMINAL = frozenset({"turn.completed", "turn.failed"})


def to_dss_events(event: str, data: str) -> list[DssEvent]:
    """The chat events one DSS frame, `event` and its `data`, carries: none,
    one, or several.

    `claim.completed` carries nothing chat needs, since the terminal frame
    repeats every block with its citations. An event name we do not know is
    skipped and logged, so a new DSS event cannot break a turn.

    Raises `DssProtocolError` when a frame chat relies on is malformed.
    """

    if event == _CLAIM:
        return []
    if event not in {_CREATED, _DELTA, *_TERMINAL}:
        logger.warning("dss_event=%s skipped=unknown", event)
        return []

    try:
        response = schemas.TurnResponse.model_validate_json(data)
    except ValidationError as exc:
        # `from None`: the ValidationError's own message quotes the input.
        raise DssProtocolError(f"malformed {event} frame: {_where(exc)}") from None
    if event == _CREATED:
        return [
            DssStarted(
                assistant_message_id=response.context.res_message_id,
                trace_id=response.context.trace_id,
            )
        ]
    if event == _DELTA:
        return [
            DssDelta(item.text)
            for item in response.message.content
            if item.type == "output_text_delta" and item.text is not None
        ]
    return [DssFinished(_answer(event, response.message))]


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
    if item.type == "form":
        return _form(item)
    if item.type == "form_error":
        return _form_error(item)
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


def _form(item: schemas.ContentItem) -> FormBlock:
    # Without its id and context the client cannot send the form back.
    if item.form_id is None or item.context is None:
        raise DssProtocolError("malformed form item: formId or context missing")
    if not all(isinstance(f, schemas.FormField) for f in item.fields):
        raise DssProtocolError("malformed form item: a field has no kind")
    return FormBlock(
        form_id=item.form_id,
        context=item.context,
        fields=tuple(
            FormField(
                name=f.name,
                label=f.label,
                kind=f.kind,
                required=f.required,
                pattern=f.pattern,
                min_length=f.min_length,
                max_length=f.max_length,
                options=tuple(
                    FormOption(value=o.value, label=o.label) for o in f.options
                ),
            )
            for f in item.fields
            if isinstance(f, schemas.FormField)
        ),
    )


def _form_error(item: schemas.ContentItem) -> FormErrorBlock:
    # Without these the client cannot tell which form, or which send, it is.
    if item.form_id is None or item.context is None or item.submission_id is None:
        raise DssProtocolError(
            "malformed form_error item: formId, context or submissionId missing"
        )
    if not all(isinstance(f, schemas.FieldError) for f in item.fields):
        raise DssProtocolError("malformed form_error item: a field has no error")
    return FormErrorBlock(
        form_id=item.form_id,
        context=item.context,
        submission_id=item.submission_id,
        fields=tuple(
            FieldError(name=f.name, label=f.label, error=f.error)
            for f in item.fields
            if isinstance(f, schemas.FieldError)
        ),
    )
