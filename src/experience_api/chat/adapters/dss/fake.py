"""A stand-in DSS that plays canned turns.

It lets the API run with no DSS behind it: for tests, and for the web client to
try the real API. It ignores what the turn asks and plays the same answer every
time, the one in the contract's examples.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable
from uuid import uuid4

from experience_api.chat.domain import (
    Answer,
    ChatTurn,
    Citation,
    DssDelta,
    DssEvent,
    DssFinished,
    DssStarted,
    Outcome,
    Source,
    TextBlock,
)

# Contract §5.1 and §5.2.
_ANSWERED_DELTAS = ("Tomorrow in Nashik ", "expect light rain after 3 pm.")
_ANSWERED = Answer(
    outcome=Outcome(status="answered", cause=None),
    content=(
        TextBlock(
            text="".join(_ANSWERED_DELTAS),
            citations=(Citation(source_id="src_1", start=0, end=48),),
        ),
    ),
    sources=(Source(id="src_1", name="IMD", url="https://mausam.imd.gov.in/"),),
)


class FakeDssClient:
    def __init__(self, *, new_id: Callable[[], str] = lambda: str(uuid4())) -> None:
        # Each turn gets its own assistant message id, as from the real DSS: the
        # client keys its chat bubbles on it.
        self._new_id = new_id

    async def stream_turn(
        self, turn: ChatTurn, *, transaction_id: str
    ) -> AsyncGenerator[DssEvent]:
        yield DssStarted(assistant_message_id=self._new_id(), trace_id=transaction_id)
        for piece in _ANSWERED_DELTAS:
            yield DssDelta(piece)
        yield DssFinished(_ANSWERED)
