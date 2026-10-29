"""The contract's own examples, as test data. One copy, so a test and the
contract cannot drift apart silently."""

from typing import Any

from experience_api.chat.domain import (
    Channel,
    ChatTurn,
    FieldValue,
    FormSubmission,
    Location,
    Message,
)

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

# Contract §7: the network participant a deployment serves.
SENDER_ID = "exp-karnataka.da.gov.in"

# The same request as a turn, with no channel sent: the default, `web`.
FOLLOW_UP_TURN = ChatTurn(
    session_id="68a3872f-3f0d-4cf6-99a3-a350132a0080",
    message_id="1ab38d6c-6fdb-4849-8ea1-da5e80a8687c",
    query="And what about tomorrow?",
    history=(
        Message("user", "What is the weather today at my location?"),
        Message("assistant", "Nashik is clear today, 31°C, no rain expected."),
    ),
    source_language="en",
    target_language="en",
    location=Location(latitude=20.0059, longitude=73.7898),
    channel=Channel.WEB,
)

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

# What the fake DSS answers, as the client receives it. Longer than the
# contract's one-liner, streamed in pieces that break mid-word the way a model's
# do, and not all ASCII, so the client sees realistic text.
FAKE_PIECES = [
    "Tomorrow in Nashik expect light ",
    "rain after 3 pm, with about 4 mm through the eve",
    "ning. Temperatures stay between 22°C and 30°C, ",
    "so field work is best done before noon. ",
    "If you plan to spray, wait until ",
    "the day after",
    ", when the forecast is dry",
    ".",
]
FAKE_TEXT = "".join(FAKE_PIECES)
FAKE_ANSWERED: dict[str, Any] = {
    **{k: ANSWERED[k] for k in ("sessionId", "messageId")},
    "assistantMessageId": ANSWERED["assistantMessageId"],
    "traceId": ANSWERED["traceId"],
    "outcome": {"status": "answered", "cause": None},
    "content": [
        {
            "type": "text",
            "text": FAKE_TEXT,
            "citations": [{"sourceId": "src_1", "start": 0, "end": len(FAKE_TEXT)}],
        }
    ],
    "sources": [{"id": "src_1", "name": "IMD", "url": "https://mausam.imd.gov.in/"}],
}

# Contract §7: what the API sends the DSS for FOLLOW_UP.
DSS_REQUEST: dict[str, Any] = {
    "context": {
        "id": "api.dss.turn",
        "timestamp": "2026-09-23T08:00:00Z",
        "sessionId": "68a3872f-3f0d-4cf6-99a3-a350132a0080",
        "transactionId": "3c67dc05-6ba2-4ab4-bb7c-377e16a5ab5b",
        "messageId": "1ab38d6c-6fdb-4849-8ea1-da5e80a8687c",
        "senderId": SENDER_ID,
    },
    "message": {
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "What is the weather today at my location?",
                    }
                ],
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "Nashik is clear today, 31°C, no rain expected.",
                    }
                ],
            },
            {
                "role": "user",
                "content": [{"type": "text", "text": "And what about tomorrow?"}],
            },
        ],
        "attributes": {
            "channel": "web",
            "sourceLanguage": "en",
            "targetLanguage": "en",
            "location": {
                "geometry": {"type": "Point", "coordinates": [73.7898, 20.0059]}
            },
            "response": {"maxCharacters": 1200},
        },
        "userContext": [{"type": "identity", "userId": "anonymous"}],
    },
}

# Contract §4.2: a filled form sent back, in place of `query`.
FORM_CONTEXT = {"scheme": "PMFBY", "category": "Grievance", "action": "support"}
FORM_SENT: dict[str, Any] = {
    "sessionId": "68a3872f-3f0d-4cf6-99a3-a350132a0080",
    "messageId": "5b0e1c2a-7d4f-4a8e-9c3b-1f2e3d4c5b6a",
    "content": [
        {
            "type": "form",
            "formId": "f-1",
            "context": FORM_CONTEXT,
            "submissionId": "9e8d7c6b-5a4f-4e3d-8c2b-1a0f9e8d7c6b",
            "fields": [
                {"name": "applicantPhone", "value": "9876543210"},
                {"name": "season", "value": ""},
            ],
        }
    ],
    "history": [],
    "language": {"source": "en", "target": "en"},
}

# The same request as a turn.
FORM_SENT_TURN = ChatTurn(
    session_id="68a3872f-3f0d-4cf6-99a3-a350132a0080",
    message_id="5b0e1c2a-7d4f-4a8e-9c3b-1f2e3d4c5b6a",
    query=FormSubmission(
        form_id="f-1",
        context=FORM_CONTEXT,
        submission_id="9e8d7c6b-5a4f-4e3d-8c2b-1a0f9e8d7c6b",
        values=(
            FieldValue("applicantPhone", "9876543210"),
            FieldValue("season", ""),
        ),
    ),
    history=(),
    source_language="en",
    target_language="en",
    location=None,
    channel=Channel.WEB,
)
