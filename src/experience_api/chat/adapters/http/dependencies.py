"""What FastAPI hands the chat route. Built once in `app.py`'s lifespan."""

from __future__ import annotations

from fastapi import Request

from experience_api.chat.service import ChatService


def get_chat_service(request: Request) -> ChatService:
    return request.app.state.chat_service
