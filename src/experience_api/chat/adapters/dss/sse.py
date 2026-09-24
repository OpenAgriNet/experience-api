"""Reading Server-Sent Events, the way the WHATWG spec says to.

Only what the DSS uses is kept: `event` and `data`. Comment lines (`:`), `id`,
`retry` and unknown fields are skipped. A frame ends at a blank line; one the
stream stops inside of is dropped, as the spec requires, and the caller sees the
stream end.

Bytes arrive in whatever chunks the network gives, which can split a line, a
CRLF or a multi-byte character. Nothing here depends on where the splits fall.
A byte-order mark at the start is dropped.

One deliberate departure from the spec: invalid UTF-8 raises
`UnicodeDecodeError` rather than being replaced with U+FFFD. A turn that fails
loudly beats an answer shown to a farmer with garbled characters in it.
"""

from __future__ import annotations

import codecs
import re
from collections.abc import AsyncIterable, AsyncIterator, Iterator
from dataclasses import dataclass, field

_LINE_END = re.compile(r"\r\n|\r|\n")


@dataclass(frozen=True)
class Frame:
    event: str
    data: str


async def parse(chunks: AsyncIterable[bytes]) -> AsyncIterator[Frame]:
    decoder = codecs.getincrementaldecoder("utf-8")()
    pending = _Pending()
    buffer = ""
    started = False
    async for chunk in chunks:
        text = decoder.decode(chunk)
        if not started and text:
            # One byte-order mark at the very start is not content (spec).
            text, started = text.removeprefix("\ufeff"), True
        buffer += text
        lines, buffer = _complete_lines(buffer, final=False)
        for frame in pending.feed(lines):
            yield frame
    lines, _ = _complete_lines(buffer + decoder.decode(b"", final=True), final=True)
    for frame in pending.feed(lines):
        yield frame


def _complete_lines(buffer: str, *, final: bool) -> tuple[list[str], str]:
    """Split off every line that has ended, and return the rest.

    A `\\r` at the very end is held back unless the stream is over: the next
    chunk may start with the `\\n` that makes it one CRLF.
    """

    lines: list[str] = []
    while match := _LINE_END.search(buffer):
        if match.group() == "\r" and match.end() == len(buffer) and not final:
            break
        lines.append(buffer[: match.start()])
        buffer = buffer[match.end() :]
    return lines, buffer


@dataclass
class _Pending:
    """The frame being read."""

    event: str = ""
    data: list[str] = field(default_factory=list)

    def feed(self, lines: list[str]) -> Iterator[Frame]:
        for line in lines:
            if not line:
                if self.data:
                    yield Frame(self.event or "message", "\n".join(self.data))
                self.event, self.data = "", []
                continue
            if line.startswith(":"):
                continue
            name, _, value = line.partition(":")
            value = value.removeprefix(" ")
            if name == "event":
                self.event = value
            elif name == "data":
                self.data.append(value)
