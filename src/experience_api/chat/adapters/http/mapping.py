"""The client's wire shapes to and from the domain. Pure functions."""

from __future__ import annotations

from pydantic import BaseModel

from experience_api.chat.adapters.http import schemas
from experience_api.chat.domain import (
    Answer,
    Block,
    ChatEvent,
    ChatTurn,
    Completed,
    Delta,
    Location,
    Message,
    RefusalBlock,
    Started,
    TurnIds,
)


def to_chat_turn(body: schemas.ChatRequest) -> ChatTurn:
    location = body.location
    return ChatTurn(
        session_id=body.session_id,
        message_id=body.message_id,
        query=body.query,
        history=tuple(Message(item.role, item.text) for item in body.history),
        source_language=body.language.source,
        target_language=body.language.target,
        location=(
            Location(latitude=location.latitude, longitude=location.longitude)
            if location
            else None
        ),
    )


def to_final_answer(ids: TurnIds, answer: Answer) -> schemas.FinalAnswer:
    error = answer.error
    return schemas.FinalAnswer(
        session_id=ids.session_id,
        message_id=ids.message_id,
        assistant_message_id=ids.assistant_message_id,
        trace_id=ids.trace_id,
        outcome=schemas.Outcome(
            status=answer.outcome.status, cause=answer.outcome.cause
        ),
        content=[_block(block) for block in answer.content],
        sources=[
            schemas.Source(id=s.id, name=s.name, url=s.url) for s in answer.sources
        ],
        error=(
            schemas.Error(
                code=error.code,
                message=error.message,
                retryable=error.retryable,
                retry_after_seconds=error.retry_after_seconds,
            )
            if error
            else None
        ),
    )


def _block(block: Block) -> schemas.TextContent | schemas.RefusalContent:
    if isinstance(block, RefusalBlock):
        return schemas.RefusalContent(text=block.text)
    return schemas.TextContent(
        text=block.text,
        citations=[
            schemas.Citation(source_id=c.source_id, start=c.start, end=c.end)
            for c in block.citations
        ],
    )


def to_wire_event(event: ChatEvent) -> tuple[str, BaseModel]:
    """The event's name on the stream, and its data."""

    match event:
        case Started(ids):
            return "started", schemas.StartedEvent(
                session_id=ids.session_id,
                message_id=ids.message_id,
                assistant_message_id=ids.assistant_message_id,
                trace_id=ids.trace_id,
            )
        case Delta(text):
            return "delta", schemas.DeltaEvent(text=text)
        case Completed(ids, answer):
            return "completed", to_final_answer(ids, answer)
