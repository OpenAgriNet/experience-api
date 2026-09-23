"""The contract's own examples, as test data. One copy, so a test and the
contract cannot drift apart silently."""

from typing import Any

# Contract §4, the follow-up request.
FOLLOW_UP: dict[str, Any] = {
    "sessionId": "68a3872f-3f0d-4cf6-99a3-a350132a0080",
    "messageId": "1ab38d6c-6fdb-4849-8ea1-da5e80a8687c",
    "query": "And what about tomorrow?",
    "history": [
        {"role": "user", "text": "What is the weather today at my location?"},
        {"role": "assistant", "text": "Nashik is clear today, 31°C, no rain expected."},
    ],
    "language": {"source": "en", "target": "en"},
    "location": {"latitude": 20.0059, "longitude": 73.7898},
}

# Contract §5.2, the answered FinalAnswer.
ANSWERED: dict[str, Any] = {
    "sessionId": "68a3872f-3f0d-4cf6-99a3-a350132a0080",
    "messageId": "1ab38d6c-6fdb-4849-8ea1-da5e80a8687c",
    "assistantMessageId": "8d2f4b61-93c7-4e0a-b1f5-2a7c9e3d6f10",
    "traceId": "3c67dc05-6ba2-4ab4-bb7c-377e16a5ab5b",
    "outcome": {"status": "answered", "cause": None},
    "content": [
        {
            "type": "text",
            "text": "Tomorrow in Nashik expect light rain after 3 pm.",
            "citations": [{"sourceId": "src_1", "start": 0, "end": 48}],
        }
    ],
    "sources": [{"id": "src_1", "name": "IMD", "url": "https://mausam.imd.gov.in/"}],
}
