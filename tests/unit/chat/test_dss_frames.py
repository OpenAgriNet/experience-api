"""DSS frames become chat's DSS events (contract §7.1).

Reading is lenient: the DSS may add fields, events and content types in any
`/v1` release, and none of them may break a turn.
"""

import json
import logging

import pytest

from experience_api.chat.adapters.dss.mapping import DssProtocolError, to_dss_events
from experience_api.chat.adapters.dss.sse import Frame
from experience_api.chat.domain import (
    Answer,
    Citation,
    DssDelta,
    DssEvent,
    DssFinished,
    DssStarted,
    Outcome,
    RefusalBlock,
    Source,
    TextBlock,
    TurnError,
)
from tests.support import dss_streams
from tests.support.dss_streams import CONTEXT, frame


def _events(raw: bytes) -> list[DssEvent]:
    events: list[DssEvent] = []
    for chunk in raw.decode().split("\n\n"):
        if not chunk:
            continue
        name, data = (line.split(": ", 1)[1] for line in chunk.split("\n"))
        events += to_dss_events(Frame(name, data))
    return events


def test_a_real_dss_stream() -> None:
    assert _events(dss_streams.NO_MATCH) == [
        DssStarted(
            assistant_message_id="cc8a0af4525a4a43890f12b91baeeb9c",
            trace_id="3c67dc05-6ba2-4ab4-bb7c-377e16a5ab5b",
        ),
        DssFinished(
            Answer(
                outcome=Outcome(status="no_match", cause=None),
                content=(
                    TextBlock(
                        "I could not find a way to help with that. I can assist "
                        "with agriculture and livestock questions."
                    ),
                ),
                sources=(),
            )
        ),
    ]


def test_deltas_citations_refusals_and_sources() -> None:
    events = _events(dss_streams.ANSWERED)

    # claim.completed adds nothing: the terminal frame carries every block.
    assert events[1:3] == [DssDelta("Light rain "), DssDelta("after 3 pm.")]
    assert events[3] == DssFinished(
        Answer(
            outcome=Outcome(status="partially_answered", cause="out_of_scope"),
            content=(
                TextBlock(
                    "Light rain after 3 pm.",
                    citations=(Citation(source_id="src_1", start=0, end=22),),
                ),
                RefusalBlock("I cannot give seed prices."),
            ),
            sources=(Source(id="src_1", name="IMD", url="https://mausam.imd.gov.in/"),),
        )
    )
    assert len(events) == 4


def test_a_failed_turn_is_an_answer_with_an_error() -> None:
    finished = _events(dss_streams.FAILED)[-1]

    assert isinstance(finished, DssFinished)
    assert finished.answer.outcome == Outcome("unavailable", "provider_unavailable")
    assert finished.answer.content == (TextBlock("The weather service is down."),)
    assert finished.answer.error == TurnError(
        code="provider_unavailable",
        message="A service this turn needed could not be reached.",
        retryable=True,
        retry_after_seconds=30,
    )


def test_unknown_fields_are_ignored() -> None:
    raw = frame("turn.created", 1, {"content": [], "sources": [], "mood": "sunny"})
    data = json.loads(raw.decode().split("data: ", 1)[1])
    data["context"]["region"] = "west"

    assert to_dss_events(Frame("turn.created", json.dumps(data))) == [
        DssStarted(
            assistant_message_id=CONTEXT["resMessageId"], trace_id=CONTEXT["traceId"]
        )
    ]


def test_an_unknown_event_is_skipped_with_a_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        assert to_dss_events(Frame("turn.thinking", "{}")) == []

    assert "turn.thinking" in caplog.text


def test_an_unknown_content_type_is_skipped() -> None:
    raw = frame(
        "turn.completed",
        2,
        {
            "outcome": {"status": "answered", "confidence": 90, "cause": None},
            "content": [{"type": "chart", "spec": {}}, {"type": "text", "text": "Hi."}],
            "sources": [],
        },
    )
    (finished,) = _events(raw)

    assert isinstance(finished, DssFinished)
    assert finished.answer.content == (TextBlock("Hi."),)


def test_a_malformed_frame_names_the_problem_but_not_the_text() -> None:
    # The DSS's text can echo the user's words; it must not reach a log line
    # through an exception message.
    secret = "my farm is at Survey No. 42"
    raw = frame(
        "turn.completed",
        2,
        {
            "outcome": {"status": "answered", "cause": None},
            "content": [{"type": "text", "text": secret}],
            "sources": [{"id": "s", "url": secret}],
        },
    )
    data = raw.decode().split("data: ", 1)[1].strip()

    with pytest.raises(DssProtocolError) as caught:
        to_dss_events(Frame("turn.completed", data))

    assert "turn.completed" in str(caught.value)
    assert "name" in str(caught.value)
    assert secret not in str(caught.value)
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__


@pytest.mark.parametrize(
    "data",
    ["not json", "[]", '{"context": {}, "message": {}}'],
    ids=["not json", "not an object", "missing ids"],
)
def test_any_malformed_frame_is_a_protocol_error(data: str) -> None:
    with pytest.raises(DssProtocolError):
        to_dss_events(Frame("turn.created", data))


def test_a_terminal_frame_without_an_outcome_is_a_protocol_error() -> None:
    raw = frame("turn.completed", 2, {"content": [], "sources": []})
    data = raw.decode().split("data: ", 1)[1].strip()

    with pytest.raises(DssProtocolError, match="outcome"):
        to_dss_events(Frame("turn.completed", data))
