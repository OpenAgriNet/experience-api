"""`ChatService` opens a DSS turn and relays it as the client's events."""

from experience_api.chat.adapters.dss.fake import FakeDssClient
from experience_api.chat.adapters.http.mapping import to_chat_turn
from experience_api.chat.adapters.http.schemas import ChatRequest
from experience_api.chat.domain import Completed, Delta, Started, TurnIds
from experience_api.chat.service import ChatService
from tests.support.examples import FOLLOW_UP

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
    assert events[1:3] == [
        Delta("Tomorrow in Nashik "),
        Delta("expect light rain after 3 pm."),
    ]
    assert isinstance(events[3], Completed)
    assert events[3].ids == ids
    assert events[3].answer.outcome.status == "answered"
    assert len(events) == 4


async def test_each_turn_gets_its_own_transaction_id() -> None:
    ids = iter(["tx-1", "tx-2"])
    service = ChatService(FakeDssClient(), new_id=lambda: next(ids))

    first = await anext(await service.open(TURN))
    second = await anext(await service.open(TURN))

    assert isinstance(first, Started) and isinstance(second, Started)
    assert (first.ids.trace_id, second.ids.trace_id) == ("tx-1", "tx-2")
