"""`ChatService` opens a DSS turn and relays it as the client's events."""

from experience_api.chat.adapters.dss.fake import FakeDssClient
from experience_api.chat.adapters.http.mapping import to_chat_turn
from experience_api.chat.adapters.http.schemas import ChatRequest
from experience_api.chat.domain import (
    Completed,
    Delta,
    DssDelta,
    DssStarted,
    Started,
    TurnIds,
)
from experience_api.chat.service import ChatService
from tests.support.examples import FAKE_PIECES, FOLLOW_UP

TURN = to_chat_turn(ChatRequest.model_validate(FOLLOW_UP))


def _service() -> ChatService:
    return ChatService(
        FakeDssClient(new_id=lambda: "assistant-1"), new_id=lambda: "tx-1"
    )


async def test_relays_the_turn_with_its_ids() -> None:
    events = [e async for e in await _service().open(TURN)]

    ids = TurnIds(
        session_id=TURN.session_id,
        message_id=TURN.message_id,
        assistant_message_id="assistant-1",
        trace_id="tx-1",
    )
    assert events[0] == Started(ids)
    assert events[1:-1] == [Delta(piece) for piece in FAKE_PIECES]
    completed = events[-1]
    assert isinstance(completed, Completed)
    assert completed.ids == ids
    assert completed.answer.outcome.status == "answered"


async def test_each_turn_gets_its_own_transaction_id() -> None:
    ids = iter(["tx-1", "tx-2"])
    service = ChatService(FakeDssClient(), new_id=lambda: next(ids))

    first = await anext(await service.open(TURN))
    second = await anext(await service.open(TURN))

    assert isinstance(first, Started) and isinstance(second, Started)
    assert (first.ids.trace_id, second.ids.trace_id) == ("tx-1", "tx-2")


class _Broken(FakeDssClient):
    """A DSS stream that starts, sends one piece, then stops with no answer."""

    async def stream_turn(self, turn, *, transaction_id):  # type: ignore[override]
        yield DssStarted(assistant_message_id="a", trace_id=transaction_id)
        yield DssDelta("half an ans")


async def test_a_stream_with_no_answer_ends_without_one_for_now() -> None:
    # Pins today's gap: no terminal event reaches the client. The client treats
    # a stream that closes this way as `upstream_error` (contract §5.1), but the
    # API should say so itself. Phase 4 replaces this with that error.
    events = [e async for e in await ChatService(_Broken(), new_id=str).open(TURN)]

    assert [type(e) for e in events] == [Started, Delta]
