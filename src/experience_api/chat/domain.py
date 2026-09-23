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


# ---------------------------------------------------------------------------
# The answer, as the DSS gives it. Its text is passed through untouched.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Citation:
    """`start` and `end` are Unicode code-point offsets into the block's text."""

    source_id: str
    start: int
    end: int


@dataclass(frozen=True)
class TextBlock:
    text: str
    citations: tuple[Citation, ...] = ()


@dataclass(frozen=True)
class RefusalBlock:
    text: str


Block = TextBlock | RefusalBlock


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    url: str | None = None


@dataclass(frozen=True)
class Outcome:
    """`status` and `cause` are open sets, passed through as strings."""

    status: str
    cause: str | None


@dataclass(frozen=True)
class TurnError:
    """A turn the DSS finished but could not answer, because something it
    needed was down."""

    code: str
    message: str
    retryable: bool
    retry_after_seconds: int | None = None


@dataclass(frozen=True)
class Answer:
    outcome: Outcome
    content: tuple[Block, ...]
    sources: tuple[Source, ...]
    error: TurnError | None = None


@dataclass(frozen=True)
class TurnIds:
    """The ids a response is filed under. `trace_id` is the DSS's name for
    this attempt; the client shows it when something goes wrong."""

    session_id: str
    message_id: str
    assistant_message_id: str
    trace_id: str


# ---------------------------------------------------------------------------
# What a DSS turn yields, in order: one DssStarted, any number of DssDelta, one
# DssFinished.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DssStarted:
    """The DSS accepted the turn."""

    assistant_message_id: str
    trace_id: str


@dataclass(frozen=True)
class DssDelta:
    """A piece of answer text, exactly as the DSS wrote it."""

    text: str


@dataclass(frozen=True)
class DssFinished:
    answer: Answer


DssEvent = DssStarted | DssDelta | DssFinished


# ---------------------------------------------------------------------------
# What ChatService yields for the client, in order: one Started, any number of
# Delta, one Completed.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Started:
    ids: TurnIds


@dataclass(frozen=True)
class Delta:
    """Passed through from the DSS unchanged. The API adds no separators."""

    text: str


@dataclass(frozen=True)
class Completed:
    """The authoritative answer. It replaces whatever the deltas built up."""

    ids: TurnIds
    answer: Answer


ChatEvent = Started | Delta | Completed
