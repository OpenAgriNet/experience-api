"""The client's wire shapes, contract §4 and §5. Field names live here and nowhere else.

The wire is camelCase and Python is snake_case. Aliases bridge the two here, so
nothing inward sees a camelCase name. Inbound models accept camelCase only: a
snake_case key is an unknown field, and unknown fields are rejected.

Every rule the DSS checks is checked here too (ADR-0001 §5.5). A request the DSS
would reject must never reach it.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    SerializerFunctionWrapHandler,
    model_serializer,
    model_validator,
)
from pydantic.alias_generators import to_camel

from experience_api.chat.domain import Channel

# BCP 47, the same pattern the DSS applies.
BCP47 = r"^[A-Za-z]{2,3}(-[A-Za-z0-9]{1,8})*$"


def _not_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("must not be empty")
    return value


# Kept as sent, not trimmed: the DSS gets the user's words unchanged.
Text = Annotated[str, AfterValidator(_not_blank)]
LanguageCode = Annotated[str, Field(pattern=BCP47)]
# A UUID in its canonical hyphenated form, any case. Kept a string, never parsed
# into `uuid.UUID`: the API passes ids back exactly as the client sent them
# (contract §3), and parsing would lowercase them.
Uuid = Annotated[
    str,
    Field(
        pattern=r"^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$"
    ),
]


class _WireIn(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=False, extra="forbid", frozen=True
    )


class HistoryItem(_WireIn):
    role: Literal["user", "assistant"]
    text: Text


class Language(_WireIn):
    source: LanguageCode
    target: LanguageCode


class Location(_WireIn):
    # Strict: a JSON number only, never `true` or `"20.5"`. Finite: Python's JSON
    # parser reads `NaN` and `Infinity`, which no coordinate can be.
    latitude: float = Field(ge=-90, le=90, strict=True, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, strict=True, allow_inf_nan=False)


class SubmittedField(_WireIn):
    name: Text
    # May be empty: an optional field left blank. The DSS checks the rules.
    value: str = Field(strict=True)


class FormSubmission(_WireIn):
    """A filled form sent back, contract §4.2. Only its shape is checked here."""

    type: Literal["form"]
    form_id: Text
    # Opaque: sent back exactly as the `form` item gave it.
    context: dict[str, Annotated[str, Field(strict=True)]]
    submission_id: Uuid
    fields: list[SubmittedField]


class ChatRequest(_WireIn):
    session_id: Uuid
    message_id: Uuid
    # Exactly one of `query` and `content` (contract §4): the DSS takes one
    # kind of message per turn.
    query: Text | None = None
    content: (
        Annotated[list[FormSubmission], Field(min_length=1, max_length=1)] | None
    ) = None
    history: list[HistoryItem]
    language: Language
    location: Location | None = None
    # Both an absent key and an explicit `null` mean the deployment's default
    # (contract §4). The mapping fills it in.
    channel: Channel | None = None

    @model_validator(mode="after")
    def _one_message(self) -> Self:
        if (self.query is None) == (self.content is None):
            raise ValueError("send exactly one of query and content")
        return self


# ---------------------------------------------------------------------------
# Outbound, contract §5.2. Built by field name, sent as camelCase.
# ---------------------------------------------------------------------------


class _WireOut(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, extra="forbid", frozen=True
    )


def wire(model: BaseModel) -> dict[str, Any]:
    """A model as the client receives it: camelCase, optional fields left out.

    A field the contract marks required but nullable, such as `outcome.cause`,
    is kept as `null` by its own model.
    """

    return model.model_dump(mode="json", by_alias=True, exclude_none=True)


class Citation(_WireOut):
    source_id: str
    start: int
    end: int


class TextContent(_WireOut):
    type: Literal["text"] = "text"
    text: str
    citations: list[Citation]


class RefusalContent(_WireOut):
    type: Literal["refusal"] = "refusal"
    text: str


class FormOption(_WireOut):
    value: str
    label: str


class FormField(_WireOut):
    name: str
    label: str
    kind: str
    required: bool
    pattern: str | None = None
    min_length: int | None = None
    max_length: int | None = None
    options: list[FormOption] | None = None


class FormContent(_WireOut):
    type: Literal["form"] = "form"
    form_id: str
    context: dict[str, str]
    fields: list[FormField]


class FormFieldError(_WireOut):
    name: str
    label: str
    error: str


class FormErrorContent(_WireOut):
    type: Literal["form_error"] = "form_error"
    form_id: str
    context: dict[str, str]
    submission_id: str
    # Kept when empty: `[]` means the office could not take the form.
    fields: list[FormFieldError]


class Source(_WireOut):
    id: str
    name: str
    url: str | None = None


class Outcome(_WireOut):
    status: str
    cause: str | None

    @model_serializer(mode="wrap")
    def _keep_null_cause(self, handler: SerializerFunctionWrapHandler) -> Any:
        # `exclude_none` would drop it; the contract says required, may be null.
        data = handler(self)
        data.setdefault("cause", None)
        return data


class Error(_WireOut):
    code: str
    message: str
    retryable: bool
    retry_after_seconds: int | None = None


class FinalAnswer(_WireOut):
    session_id: str
    message_id: str
    assistant_message_id: str
    trace_id: str
    outcome: Outcome
    content: list[TextContent | RefusalContent | FormContent | FormErrorContent]
    sources: list[Source]
    error: Error | None = None


# ---------------------------------------------------------------------------
# Stream events, contract §5.1. `completed` carries a FinalAnswer. Each frame's
# data also carries `sequence`, which the framing adds.
# ---------------------------------------------------------------------------


class StartedEvent(_WireOut):
    session_id: str
    message_id: str
    assistant_message_id: str
    trace_id: str


class DeltaEvent(_WireOut):
    text: str
