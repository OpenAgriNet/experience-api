"""ChatService: send a turn to the DSS and relay it as the client's events.

It owns the stream's promises to the client (contract §5.1): the deltas pass
through unchanged, and the stream ends with one `Completed`.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable
from contextlib import aclosing

from experience_api.chat.domain import (
    ChatEvent,
    ChatTurn,
    Completed,
    Delta,
    DssDelta,
    DssEvent,
    DssFinished,
    DssStarted,
    Started,
    TurnIds,
)
from experience_api.chat.ports import DssClient


class ChatService:
    def __init__(self, dss: DssClient, *, new_id: Callable[[], str]) -> None:
        self._dss = dss
        self._new_id = new_id

    async def open(self, turn: ChatTurn) -> AsyncGenerator[ChatEvent]:
        """Start the turn, and return its events once the DSS has accepted it.

        Returning only after acceptance means anything that fails before then
        can still become an HTTP status; the response has not started.
        """

        # One id per attempt: a retry of the same message gets a new one.
        stream = self._dss.stream_turn(turn, transaction_id=self._new_id())
        accepted = False
        try:
            first = await anext(stream)
            if not isinstance(first, DssStarted):
                raise RuntimeError(f"the DSS stream opened with {first!r}")
            accepted = True
        finally:
            if not accepted:
                await stream.aclose()

        ids = TurnIds(
            session_id=turn.session_id,
            message_id=turn.message_id,
            assistant_message_id=first.assistant_message_id,
            trace_id=first.trace_id,
        )
        return _relay(ids, stream)


async def _relay(
    ids: TurnIds, stream: AsyncGenerator[DssEvent]
) -> AsyncGenerator[ChatEvent]:
    # `aclosing`: when the reader stops early, such as a browser that went away,
    # the DSS stream is closed with it, which ends the DSS call.
    async with aclosing(stream):
        yield Started(ids)
        async for event in stream:
            if isinstance(event, DssDelta):
                yield Delta(event.text)
            # TODO(phase 4): a stream that ends before DssFinished must end
            # with an upstream_error, not silently.
            elif isinstance(event, DssFinished):
                yield Completed(ids, event.answer)
                return
