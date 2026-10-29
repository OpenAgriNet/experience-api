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
from tests.support.examples import FORM_SENT


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
        _with("language.source", "hi-IN"),
        _with("history", [{"role": "user", "text": t} for t in ("a", "b")]),
        _with("location.latitude", -90),
        _with("location.longitude", 180),
        _with("location.latitude", 20),
    ],
    ids=[
        "language with region",
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
        _with("sessionId", "68a3872f3f0d4cf699a3a350132a0080"),
        _with("sessionId", "{68a3872f-3f0d-4cf6-99a3-a350132a0080}"),
        _with("messageId", "urn:uuid:1ab38d6c-6fdb-4849-8ea1-da5e80a8687c"),
        _with("messageId", 42),
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
        "sessionId without hyphens",
        "sessionId in braces",
        "messageId as a URN",
        "messageId a number",
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


@pytest.mark.parametrize("value", ["voice", "WEB", ""])
def test_a_channel_outside_the_enum_is_rejected(value: str) -> None:
    with pytest.raises(ValidationError):
        ChatRequest.model_validate(_with("channel", value))


def test_a_missing_channel_is_none() -> None:
    assert ChatRequest.model_validate(EXAMPLE).channel is None


def test_a_null_channel_is_none() -> None:
    assert ChatRequest.model_validate(_with("channel", None)).channel is None


def test_web_is_a_channel() -> None:
    assert ChatRequest.model_validate(_with("channel", "web")).channel == "web"


# ---------------------------------------------------------------------------
# A filled form sent back, contract §4.2.
# ---------------------------------------------------------------------------


def _form_with(path: str, value: Any) -> dict[str, Any]:
    """The form example with one field of its form replaced, as `_with` does."""

    body = copy.deepcopy(FORM_SENT)
    *parents, last = f"content.0.{path}".split(".")
    node: Any = body
    for key in parents:
        node = node[int(key)] if key.isdigit() else node[key]
    if value is ...:
        del node[int(last) if last.isdigit() else last]
    else:
        node[int(last) if last.isdigit() else last] = value
    return body


def test_the_form_example_is_valid() -> None:
    request = ChatRequest.model_validate(FORM_SENT)

    assert request.query is None
    assert request.content is not None
    assert request.content[0].fields[1].value == ""


@pytest.mark.parametrize(
    "body",
    [
        FORM_SENT | {"query": "And what about tomorrow?"},
        {k: v for k, v in FORM_SENT.items() if k != "content"},
        FORM_SENT | {"content": []},
        FORM_SENT | {"content": FORM_SENT["content"] * 2},
        FORM_SENT | {"content": None},
        _form_with("type", "text"),
        _form_with("formId", ...),
        _form_with("formId", " "),
        _form_with("context", ...),
        _form_with("context", {"scheme": 1}),
        _form_with("submissionId", ...),
        _form_with("submissionId", "s-1"),
        _form_with("fields", ...),
        _form_with("fields.0.name", ""),
        _form_with("fields.0.value", ...),
        _form_with("fields.0.value", 9876543210),
        _form_with("fields.0.label", "Phone"),
        _form_with("extra", True),
    ],
    ids=[
        "query and content both",
        "neither query nor content",
        "content empty",
        "two forms",
        "content null",
        "item not a form",
        "formId missing",
        "formId blank",
        "context missing",
        "context value not a string",
        "submissionId missing",
        "submissionId not a UUID",
        "fields missing",
        "field name empty",
        "field value missing",
        "field value a number",
        "unknown field in a field",
        "unknown field in the form",
    ],
)
def test_form_rejected(body: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        ChatRequest.model_validate(body)
