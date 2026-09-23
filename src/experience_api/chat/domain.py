"""What chat is about, in plain Python. No wire names, no framework."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Role = Literal["user", "assistant"]


@dataclass(frozen=True)
class Message:
    role: Role
    text: str


@dataclass(frozen=True)
class Location:
    latitude: float
    longitude: float


@dataclass(frozen=True)
class ChatTurn:
    """One user message and the conversation before it, as the client sent it."""

    session_id: str
    message_id: str
    query: str
    history: tuple[Message, ...]
    source_language: str
    target_language: str
    location: Location | None
