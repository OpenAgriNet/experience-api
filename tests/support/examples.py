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
