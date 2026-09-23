"""The client's wire shapes to and from the domain. Pure functions."""

from __future__ import annotations

from experience_api.chat.adapters.http import schemas
from experience_api.chat.domain import ChatTurn, Location, Message


def to_chat_turn(body: schemas.ChatRequest) -> ChatTurn:
    location = body.location
    return ChatTurn(
        session_id=str(body.session_id),
        message_id=str(body.message_id),
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
