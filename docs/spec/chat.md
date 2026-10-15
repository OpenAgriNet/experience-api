# chat

## Overview
A farmer asks a question in the web client. The client sends it to chat, with
the conversation so far, the languages, and maybe a location. Chat checks it,
asks the DSS, and passes the answer back, either as a live stream or as one
complete answer. It stores nothing. The wire shapes are in the
[API contract](../api-contracts/api-contract.md) §3–§7.

## Interfaces
**Exposes:** `POST /v1/chat`.
**Depends on:** the DSS, through its `POST /v1/turns` event stream.

## Behaviour
### Checking the request
Chat is strict. It turns away a request with a missing or unknown field, an id
that is not a UUID, empty text, a language code that is not BCP 47, or a
location out of range. The answer is a `422`, and the DSS is never called. It checks every rule the DSS checks, so a request the
DSS would reject never reaches it. The user's words are passed on unchanged.

### Answering
If the client asks for `text/event-stream`, chat streams: a `started` event,
the answer's pieces as they come, then one `completed` event that holds the
whole answer. Otherwise it waits for the end and returns that same answer as
JSON. Either way, the client's ids come back exactly as sent.

When the DSS cannot answer because something it needs is down, that is still
an answer. It arrives as `completed`, with an error inside.

### Reading the DSS
Chat is lenient here. New DSS fields, events and content types are ignored, so
a DSS release cannot break a turn.

### Without a DSS
With `DSS_MODE=fake`, chat plays one canned weather answer for every turn.

## Key flows
A streamed turn: client → chat → DSS, then `started`, `delta`…, `completed`
back. A JSON turn makes the same DSS call and returns only the end. If the
browser leaves mid-stream, chat closes the DSS call and the DSS stops.

## Non-functional
No storage, no retries, no sign-in (every turn is `anonymous`). One connection
pool to the DSS. Errors about a bad DSS frame never include its text, since it
can echo the user's words.

## Failure modes
| Scenario | Today | Recovery |
|---|---|---|
| Bad request | `422`, FastAPI's body | Client fixes it |
| DSS down or returns an error | `500` <!-- inferred — verify --> | User retries |
| DSS stream breaks or ends early | Stream stops, no `error` event <!-- inferred — verify --> | User retries |
| Browser leaves | DSS call closed | None |

## Configuration and limits
| Setting | Default | Notes |
|---|---|---|
| `EXPERIENCE_API_DSS_MODE` | `fake` | `fake` or `http` |
| `EXPERIENCE_API_DSS_BASE_URL` | `http://localhost:8077` | Checked on the first turn, not at start |
| `EXPERIENCE_API_CHANNEL` | `web` | Sent to the DSS |
| `EXPERIENCE_API_MAX_CHARACTERS` | `1200` | Sent to the DSS |
| DSS timeouts | 5 s connect, 120 s read | In code; a stopgap |

## Decisions
- 2026-09-23 Ports and adapters per feature (ADR-0001).
- 2026-09-23 FastAPI's default `422` for now; decide at peer review.
- 2026-09-24 Always stream from the DSS, even for a JSON client.
- 2026-09-24 Strict with the client, lenient with the DSS.

## Known gaps
DSS failures do not yet map to the contract's codes (`503`, `429`, `413`,
`502`, `504`). A broken stream sends no `error` event. The contract's two
timeouts are not built. No end-to-end test against a real DSS.
