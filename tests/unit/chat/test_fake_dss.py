"""The fake DSS plays the contract's `answered` example (§5.1, §5.2)."""

from experience_api.chat.adapters.dss.fake import FakeDssClient
from experience_api.chat.adapters.http.mapping import to_chat_turn
from experience_api.chat.adapters.http.schemas import ChatRequest
from experience_api.chat.domain import (
    Answer,
    Citation,
    DssDelta,
    DssFinished,
    DssStarted,
    Outcome,
    Source,
    TextBlock,
)
from experience_api.chat.ports import DssClient
from tests.support.examples import FOLLOW_UP

TURN = to_chat_turn(ChatRequest.model_validate(FOLLOW_UP))


async def test_answered_plays_the_contract_example() -> None:
    dss: DssClient = FakeDssClient(new_id=lambda: "assistant-1")

    events = [e async for e in dss.stream_turn(TURN, transaction_id="tx-1")]

    assert events == [
        DssStarted(assistant_message_id="assistant-1", trace_id="tx-1"),
        DssDelta("Tomorrow in Nashik "),
        DssDelta("expect light rain after 3 pm."),
        DssFinished(
            Answer(
                outcome=Outcome(status="answered", cause=None),
                content=(
                    TextBlock(
                        text="Tomorrow in Nashik expect light rain after 3 pm.",
                        citations=(Citation(source_id="src_1", start=0, end=48),),
                    ),
                ),
                sources=(
                    Source(id="src_1", name="IMD", url="https://mausam.imd.gov.in/"),
                ),
                error=None,
            )
        ),
    ]


async def test_the_deltas_add_up_to_the_final_text() -> None:
    events = [e async for e in FakeDssClient().stream_turn(TURN, transaction_id="t")]

    streamed = "".join(e.text for e in events if isinstance(e, DssDelta))
    final = events[-1]
    assert isinstance(final, DssFinished)
    assert isinstance(final.answer.content[0], TextBlock)
    assert streamed == final.answer.content[0].text
