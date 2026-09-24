"""Reading the DSS's Server-Sent Events, whatever chunks they arrive in."""

from collections.abc import AsyncIterator, Iterable

import pytest

from experience_api.chat.adapters.dss.sse import Frame, parse

TWO_FRAMES = (
    'event: turn.created\ndata: {"a":1}\n\n'
    'event: claim.delta\ndata: {"text":"22°C"}\n\n'
).encode()


async def _chunks(parts: Iterable[bytes]) -> AsyncIterator[bytes]:
    for part in parts:
        yield part


async def _frames(parts: Iterable[bytes]) -> list[Frame]:
    return [frame async for frame in parse(_chunks(parts))]


async def test_reads_each_frame() -> None:
    assert await _frames([TWO_FRAMES]) == [
        Frame("turn.created", '{"a":1}'),
        Frame("claim.delta", '{"text":"22°C"}'),
    ]


async def test_any_chunking_gives_the_same_frames() -> None:
    # One byte at a time splits every line, and the two bytes of the `°`.
    one_by_one = [TWO_FRAMES[i : i + 1] for i in range(len(TWO_FRAMES))]

    assert await _frames(one_by_one) == await _frames([TWO_FRAMES])


@pytest.mark.parametrize("newline", ["\r\n", "\r"], ids=["crlf", "cr"])
async def test_every_line_ending(newline: str) -> None:
    raw = TWO_FRAMES.decode().replace("\n", newline).encode()

    assert await _frames([raw]) == await _frames([TWO_FRAMES])


async def test_comments_and_unknown_fields_are_skipped() -> None:
    raw = b": ping\nid: 7\nretry: 10\nevent: x\ndata: y\n\n"

    assert await _frames([raw]) == [Frame("x", "y")]


async def test_data_lines_join_with_newlines_and_lose_one_space() -> None:
    raw = b"data:  first\ndata:second\n\n"

    assert await _frames([raw]) == [Frame("message", " first\nsecond")]


async def test_a_frame_with_no_data_is_not_a_frame() -> None:
    assert await _frames([b"event: x\n\n"]) == []


async def test_an_unfinished_last_frame_is_dropped() -> None:
    assert await _frames([b"event: x\ndata: y\n"]) == []


async def test_a_leading_byte_order_mark_is_dropped() -> None:
    # Left in, it would rename the first field and lose the first event's name.
    bom = "﻿".encode()

    assert await _frames([bom + TWO_FRAMES]) == await _frames([TWO_FRAMES])
    assert await _frames([bom[:1], bom[1:] + TWO_FRAMES]) == await _frames([TWO_FRAMES])


async def test_only_the_first_byte_order_mark_is_dropped() -> None:
    raw = "﻿data: ﻿x\n\n".encode()

    assert await _frames([raw]) == [Frame("message", "﻿x")]


async def test_invalid_utf8_fails_loudly() -> None:
    with pytest.raises(UnicodeDecodeError):
        await _frames([b"data: \xff\n\n"])
