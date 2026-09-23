"""The DSS's wire shapes. Its field names live here and nowhere else.

The DSS wire is camelCase, like ours. Models are built by field name and sent
with their aliases.

The request side is strict (`extra="forbid"`): we build it, so an unknown field
is our typo. The response side, added with the reader, is lenient.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _Request(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, extra="forbid", frozen=True
    )


def wire(model: BaseModel) -> dict[str, Any]:
    """A model as the DSS receives it: camelCase, optional fields left out."""

    return model.model_dump(mode="json", by_alias=True, exclude_none=True)


class Context(_Request):
    id: Literal["api.dss.turn"] = "api.dss.turn"
    timestamp: datetime
    session_id: str
    transaction_id: str
    message_id: str


class TextPart(_Request):
    type: Literal["text"] = "text"
    text: str


class InputMessage(_Request):
    role: Literal["user", "assistant"]
    content: list[TextPart]


class Geometry(_Request):
    type: Literal["Point"] = "Point"
    coordinates: tuple[float, float]  # [longitude, latitude], GeoJSON order


class Location(_Request):
    geometry: Geometry


class ResponseSpec(_Request):
    max_characters: int


class Attributes(_Request):
    channel: str
    source_language: str
    target_language: str
    location: Location | None = None
    response: ResponseSpec


class Identity(_Request):
    type: Literal["identity"] = "identity"
    user_id: str


class Message(_Request):
    input: list[InputMessage]
    attributes: Attributes
    user_context: list[Identity]


class TurnRequest(_Request):
    context: Context
    message: Message
