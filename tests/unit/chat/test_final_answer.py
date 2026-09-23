"""The domain's answer becomes the contract's `FinalAnswer` (§5.2)."""

from experience_api.chat.adapters.http.mapping import to_final_answer
from experience_api.chat.adapters.http.schemas import wire
from experience_api.chat.domain import (
    Answer,
    Citation,
    Outcome,
    RefusalBlock,
    Source,
    TextBlock,
    TurnError,
    TurnIds,
)
from tests.support.examples import ANSWERED

IDS = TurnIds(
    session_id="68a3872f-3f0d-4cf6-99a3-a350132a0080",
    message_id="1ab38d6c-6fdb-4849-8ea1-da5e80a8687c",
    assistant_message_id="8d2f4b61-93c7-4e0a-b1f5-2a7c9e3d6f10",
    trace_id="3c67dc05-6ba2-4ab4-bb7c-377e16a5ab5b",
)


def test_the_contract_example() -> None:
    answer = Answer(
        outcome=Outcome(status="answered", cause=None),
        content=(
            TextBlock(
                text="Tomorrow in Nashik expect light rain after 3 pm.",
                citations=(Citation(source_id="src_1", start=0, end=48),),
            ),
        ),
        sources=(Source(id="src_1", name="IMD", url="https://mausam.imd.gov.in/"),),
    )

    assert wire(to_final_answer(IDS, answer)) == ANSWERED


def test_a_refusal_has_no_citations_and_a_source_may_have_no_url() -> None:
    answer = Answer(
        outcome=Outcome(status="partially_answered", cause="out_of_scope"),
        content=(TextBlock("Sow in June."), RefusalBlock("I can't price seed.")),
        sources=(Source(id="s", name="KVK"),),
    )

    body = wire(to_final_answer(IDS, answer))

    assert body["outcome"] == {"status": "partially_answered", "cause": "out_of_scope"}
    assert body["content"] == [
        {"type": "text", "text": "Sow in June.", "citations": []},
        {"type": "refusal", "text": "I can't price seed."},
    ]
    assert body["sources"] == [{"id": "s", "name": "KVK"}]
    assert "error" not in body


def test_an_unavailable_turn_carries_its_error() -> None:
    answer = Answer(
        outcome=Outcome(status="unavailable", cause="provider_unavailable"),
        content=(),
        sources=(),
        error=TurnError(
            code="provider_unavailable",
            message="A service this turn needed could not be reached.",
            retryable=True,
            retry_after_seconds=5,
        ),
    )

    assert wire(to_final_answer(IDS, answer))["error"] == {
        "code": "provider_unavailable",
        "message": "A service this turn needed could not be reached.",
        "retryable": True,
        "retryAfterSeconds": 5,
    }
