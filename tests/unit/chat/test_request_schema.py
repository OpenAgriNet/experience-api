"""`ChatRequest` enforces contract §4. One test per rule.

Anything the DSS would reject must be rejected here first, so a DSS `4xx` always
means a bug in this API (ADR-0001 §5.5).
"""

import copy
from typing import Any

import pytest
from pydantic import ValidationError

from experience_api.chat.adapters.http.schemas import ChatRequest
from tests.support.examples import FOLLOW_UP as EXAMPLE


def _with(path: str, value: Any) -> dict[str, Any]:
    """The example with one field replaced. `path` is dotted; a list index is a
    number. The value `...` deletes the field."""

    body = copy.deepcopy(EXAMPLE)
    *parents, last = path.split(".")
    node: Any = body
    for key in parents:
        node = node[int(key)] if key.isdigit() else node[key]
    if value is ...:
        del node[int(last) if last.isdigit() else last]
    else:
        node[int(last) if last.isdigit() else last] = value
    return body


def test_the_contract_example_is_valid() -> None:
    request = ChatRequest.model_validate(EXAMPLE)

    assert request.query == "And what about tomorrow?"
    assert request.history[1].role == "assistant"
    assert request.location is not None
    assert request.location.longitude == 73.7898


@pytest.mark.parametrize(
    "body",
    [
        _with("history", []),
        _with("location", ...),
        _with("language.source", "hi-IN"),
        _with("language.target", "hi"),
        _with("history", [{"role": "user", "text": t} for t in ("a", "b")]),
        _with("location.latitude", -90),
        _with("location.longitude", 180),
        _with("location.latitude", 20),
    ],
    ids=[
        "empty history",
        "no location",
        "language with region",
        "different target language",
        "history need not alternate",
        "latitude at its bound",
        "longitude at its bound",
        "latitude a whole number",
    ],
)
def test_allowed_variations(body: dict[str, Any]) -> None:
    ChatRequest.model_validate(body)


@pytest.mark.parametrize(
    "body",
    [
        _with("sessionId", ...),
        _with("sessionId", "not-a-uuid"),
        _with("messageId", ...),
        _with("messageId", "42"),
        _with("query", ...),
        _with("query", ""),
        _with("query", "   \n"),
        _with("history", ...),
        _with("history.0.role", "farmer"),
        _with("history.0.text", " "),
        _with("history.0.text", ...),
        _with("language", ...),
        _with("language.source", "gujarati"),
        _with("language.target", "e"),
        _with("location.latitude", 90.1),
        _with("location.longitude", -180.1),
        _with("location.latitude", ...),
        _with("location.latitude", True),
        _with("location.latitude", "20.5"),
        _with("location.longitude", float("nan")),
        _with("location.longitude", float("inf")),
        _with("transactionId", "3c67dc05-6ba2-4ab4-bb7c-377e16a5ab5b"),
        _with("history.0.extra", True),
        _with("session_id", "68a3872f-3f0d-4cf6-99a3-a350132a0080"),
    ],
    ids=[
        "sessionId missing",
        "sessionId not a UUID",
        "messageId missing",
        "messageId not a UUID",
        "query missing",
        "query empty",
        "query blank",
        "history missing",
        "role not user or assistant",
        "history text blank",
        "history text missing",
        "language missing",
        "language a full name",
        "language too short",
        "latitude over 90",
        "longitude under -180",
        "location without latitude",
        "latitude a bool",
        "latitude a string",
        "longitude NaN",
        "longitude infinite",
        "unknown top-level field",
        "unknown field in history",
        "snake_case key",
    ],
)
def test_rejected(body: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        ChatRequest.model_validate(body)
