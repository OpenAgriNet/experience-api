"""The fake DSS answers every turn the same way: a few sentences, in pieces."""

from experience_api.chat.adapters.dss.fake import FakeDssClient
from experience_api.chat.domain import (
    ChatTurn,
    Citation,
    DssDelta,
    DssFinished,
    DssStarted,
    TextBlock,
)
from experience_api.chat.ports import DssClient
from tests.support.examples import FAKE_PIECES, FAKE_TEXT

TURN = ChatTurn(
    session_id="s",
    message_id="m",
    query="And what about tomorrow?",
    history=(),
    source_language="en",
    target_language="en",
    location=None,
)


async def test_starts_streams_the_pieces_then_finishes() -> None:
    dss: DssClient = FakeDssClient(new_id=lambda: "assistant-1")

    events = [e async for e in dss.stream_turn(TURN, transaction_id="tx-1")]

    assert events[0] == DssStarted(assistant_message_id="assistant-1", trace_id="tx-1")
    assert events[1:-1] == [DssDelta(piece) for piece in FAKE_PIECES]
    finished = events[-1]
    assert isinstance(finished, DssFinished)
    assert finished.answer.outcome.status == "answered"
    assert finished.answer.content == (
        TextBlock(
            text=FAKE_TEXT,
            citations=(Citation(source_id="src_1", start=0, end=len(FAKE_TEXT)),),
        ),
    )
