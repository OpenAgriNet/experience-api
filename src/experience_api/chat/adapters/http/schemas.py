"""The client's wire shapes, contract §4. Field names live here and nowhere else.

The wire is camelCase and Python is snake_case. Aliases bridge the two here, so
nothing inward sees a camelCase name. Inbound models accept camelCase only: a
snake_case key is an unknown field, and unknown fields are rejected.

Every rule the DSS checks is checked here too (ADR-0001 §5.5). A request the DSS
would reject must never reach it.
"""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

# BCP 47, the same pattern the DSS applies.
BCP47 = r"^[A-Za-z]{2,3}(-[A-Za-z0-9]{1,8})*$"


def _not_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("must not be empty")
    return value


# Kept as sent, not trimmed: the DSS gets the user's words unchanged.
Text = Annotated[str, AfterValidator(_not_blank)]
LanguageCode = Annotated[str, Field(pattern=BCP47)]


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
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class ChatRequest(_WireIn):
    session_id: UUID
    message_id: UUID
    query: Text
    history: list[HistoryItem]
    language: Language
    location: Location | None = None
