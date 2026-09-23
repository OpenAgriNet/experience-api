"""A stand-in DSS that plays canned turns.

It lets the API run with no DSS behind it: for tests, and for the web client to
try the real API. It ignores what the turn asks and plays the same answer every
time: a short weather answer shaped like the contract's example.
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

# A few sentences, streamed in pieces that break mid-word the way a model's do,
# and not all ASCII, so the client sees realistic text. Same shape as the
# contract's §5.2 example, longer.
_ANSWERED_DELTAS = (
    "Tomorrow in Nashik expect light ",
    "rain after 3 pm, with about 4 mm through the eve",
    "ning. Temperatures stay between 22°C and 30°C, ",
    "so field work is best done before noon. ",
    "If you plan to spray, wait until ",
    "the day after",
    ", when the forecast is dry",
    ".",
)
_ANSWERED_TEXT = "".join(_ANSWERED_DELTAS)
_ANSWERED = Answer(
    outcome=Outcome(status="answered", cause=None),
    content=(
        TextBlock(
            text=_ANSWERED_TEXT,
            # The whole block cites the one source; offsets are code points.
            citations=(Citation(source_id="src_1", start=0, end=len(_ANSWERED_TEXT)),),
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
