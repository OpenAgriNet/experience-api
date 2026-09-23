"""What chat needs from the outside, in chat's terms."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Protocol

from experience_api.chat.domain import ChatTurn, DssEvent


class DssClient(Protocol):
    def stream_turn(
        self, turn: ChatTurn, *, transaction_id: str
    ) -> AsyncGenerator[DssEvent]:
        """Send one turn and yield its events in order: `DssStarted`, then
        `DssDelta`s, then `DssFinished`.

        `transaction_id` identifies this attempt in the DSS's traces. The caller
        closes the generator when it stops reading, which ends the DSS call.
        """
        ...

    async def aclose(self) -> None:
        """Release what the client holds, such as a connection pool."""
        ...
