"""DSS streams, as the DSS writes them, for the adapter's tests.

`NO_MATCH` is `dss/no-match.sse`, captured byte for byte from a running DSS
(v1.0.0) given `DSS_REQUEST` in `examples.py`. The others are built from the
DSS's wire models (`adapters/http/v1/schema.py` in its repo), for outcomes a
local DSS with no provider network cannot produce.
"""

import json
from pathlib import Path
from typing import Any

CONTEXT: dict[str, Any] = {
    "id": "api.dss.turn",
    "version": "v1.0.0",
    "timestamp": "2026-09-23T19:51:52.622320Z",
    "messageId": "1ab38d6c-6fdb-4849-8ea1-da5e80a8687c",
    "sessionId": "68a3872f-3f0d-4cf6-99a3-a350132a0080",
    "traceId": "3c67dc05-6ba2-4ab4-bb7c-377e16a5ab5b",
    "resMessageId": "cc8a0af4525a4a43890f12b91baeeb9c",
    "transactionId": "3c67dc05-6ba2-4ab4-bb7c-377e16a5ab5b",
}


def frame(event: str, sequence: int, message: dict[str, Any]) -> bytes:
    data = {"context": {**CONTEXT, "sequenceNumber": sequence}, "message": message}
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode()


NO_MATCH = (Path(__file__).parent / "dss" / "no-match.sse").read_bytes()

_TEXT = "Light rain after 3 pm."
_SOURCE = {
    "id": "src_1",
    "name": "IMD",
    "kind": "provider",
    "url": "https://mausam.imd.gov.in/",
}
_CITATION = {
    "type": "url_citation",
    "sourceId": "src_1",
    "startIndex": 0,
    "endIndex": len(_TEXT),
    "url": "https://mausam.imd.gov.in/",
    "sourceName": "IMD",
}

ANSWERED = b"".join(
    [
        frame("turn.created", 1, {"content": [], "sources": []}),
        frame(
            "claim.delta",
            2,
            {"content": [{"type": "output_text_delta", "text": "Light rain "}]},
        ),
        frame(
            "claim.delta",
            3,
            {"content": [{"type": "output_text_delta", "text": "after 3 pm."}]},
        ),
        frame(
            "claim.completed",
            4,
            {
                "content": [
                    {"type": "text", "text": _TEXT, "annotations": [_CITATION]}
                ],
                "sources": [_SOURCE],
            },
        ),
        frame(
            "turn.completed",
            5,
            {
                "outcome": {
                    "status": "partially_answered",
                    "confidence": 71,
                    "cause": "out_of_scope",
                },
                "content": [
                    {"type": "text", "text": _TEXT, "annotations": [_CITATION]},
                    {"type": "refusal", "text": "I cannot give seed prices."},
                ],
                "sources": [_SOURCE],
            },
        ),
    ]
)

FAILED = b"".join(
    [
        frame("turn.created", 1, {"content": [], "sources": []}),
        frame(
            "turn.failed",
            2,
            {
                "outcome": {
                    "status": "unavailable",
                    "confidence": 0,
                    "cause": "provider_unavailable",
                },
                "content": [{"type": "text", "text": "The weather service is down."}],
                "sources": [],
                "error": {
                    "code": "provider_unavailable",
                    "message": "A service this turn needed could not be reached.",
                    "retryable": True,
                    "retryAfterSeconds": 30,
                },
            },
        ),
    ]
)
