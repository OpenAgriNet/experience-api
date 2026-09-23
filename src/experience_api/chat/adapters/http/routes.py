"""`POST /v1/chat`, contract §4 and §5."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from experience_api.chat.adapters.http import sse
from experience_api.chat.adapters.http.dependencies import get_chat_service
from experience_api.chat.adapters.http.mapping import to_chat_turn
from experience_api.chat.adapters.http.schemas import ChatRequest
from experience_api.chat.service import ChatService

router = APIRouter()


@router.post("/chat")
async def chat(
    body: ChatRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> StreamingResponse:
    events = await service.open(to_chat_turn(body))
    return StreamingResponse(sse.frames(events), media_type=sse.MEDIA_TYPE)
