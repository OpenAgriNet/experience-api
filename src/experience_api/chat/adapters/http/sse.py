"""Server-Sent Events framing, contract §5.1.

This module owns the event names' wire form and the `sequence` counter: the
API's own, from 1, up by one per event. No `id:` lines, because a stream cannot
be resumed.
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import aclosing

from experience_api.chat.adapters.http.mapping import to_wire_event
from experience_api.chat.adapters.http.schemas import wire
from experience_api.chat.domain import ChatEvent

MEDIA_TYPE = "text/event-stream"


async def frames(events: AsyncGenerator[ChatEvent]) -> AsyncIterator[bytes]:
    # `aclosing`: a browser that goes away cancels this generator, and the
    # events it was reading, down to the DSS call, are closed with it.
    async with aclosing(events):
        sequence = 0
        async for event in events:
            sequence += 1
            name, data = to_wire_event(event)
            payload = json.dumps(
                {"sequence": sequence, **wire(data)},
                ensure_ascii=False,
                separators=(",", ":"),
            )
            yield f"event: {name}\ndata: {payload}\n\n".encode()
