"""`POST /v1/chat`, contract §4 and §5.

`Accept` picks the answer's form: the event stream when it names
`text/event-stream`, one JSON FinalAnswer otherwise, including when it is
absent. The DSS call is the same either way; JSON mode drains the stream.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import aclosing
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Response
from fastapi.responses import JSONResponse, StreamingResponse

from experience_api.chat.adapters.http import sse
from experience_api.chat.adapters.http.dependencies import get_chat_service
from experience_api.chat.adapters.http.mapping import to_chat_turn, to_final_answer
from experience_api.chat.adapters.http.schemas import ChatRequest, FinalAnswer, wire
from experience_api.chat.domain import ChatEvent, Completed
from experience_api.chat.service import ChatService

router = APIRouter()


@router.post(
    "/chat",
    response_model=FinalAnswer,
    responses={200: {"content": {sse.MEDIA_TYPE: {"schema": {"type": "string"}}}}},
)
async def chat(
    body: ChatRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
    accept: Annotated[str | None, Header()] = None,
) -> Response:
    events = await service.open(to_chat_turn(body))
    if _wants_stream(accept):
        return StreamingResponse(sse.frames(events), media_type=sse.MEDIA_TYPE)
    completed = await _drain(events)
    return JSONResponse(wire(to_final_answer(completed.ids, completed.answer)))


def _wants_stream(accept: str | None) -> bool:
    offered = {part.split(";")[0].strip() for part in (accept or "").split(",")}
    return sse.MEDIA_TYPE in offered


async def _drain(events: AsyncGenerator[ChatEvent]) -> Completed:
    """The authoritative answer. The deltas are dropped: `Completed` already
    carries every block."""

    async with aclosing(events):
        async for event in events:
            if isinstance(event, Completed):
                return event
    raise RuntimeError("the turn ended without an answer")
