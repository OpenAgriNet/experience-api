"""What chat is about, in plain Python. No wire names, no framework."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

Role = Literal["user", "assistant"]


class Channel(StrEnum):
    """Where a chat comes from. The members are the channels this API accepts,
    a subset of the DSS's own set. Adding one is a code change, because the DSS
    shapes each answer for its channel."""

    WEB = "web"


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
    channel: Channel


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


@dataclass(frozen=True)
class FormOption:
    value: str
    label: str


@dataclass(frozen=True)
class FormField:
    """One field the farmer fills in, with the only rules the DSS sends."""

    name: str
    label: str
    kind: str
    required: bool
    pattern: str | None = None
    min_length: int | None = None
    max_length: int | None = None
    options: tuple[FormOption, ...] = ()


@dataclass(frozen=True)
class FormBlock:
    """An empty form the DSS asks the farmer to fill in. `context` is opaque:
    the client sends it back as received, so the DSS can find the form again."""

    form_id: str
    context: Mapping[str, str]
    fields: tuple[FormField, ...]


Block = TextBlock | RefusalBlock | FormBlock


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
