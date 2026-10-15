# experience-api — component specs

The Experience API sits between the OpenAgriNet web client and the Decision
Support System (DSS). The client sends a farmer's question; the API checks it,
asks the DSS, and returns the answer in the client's shape. It stores nothing.
It also has `GET /healthz`, which says the process is up. It does not check
the DSS, so a DSS outage never takes the API down with it.

## Components

| Component | Covers | Scope |
|---|---|---|
| chat | `src/experience_api/chat/**`, `src/experience_api/settings.py`, `src/experience_api/shared/**` | Answers one chat turn: checks it, asks the DSS, streams or returns the answer |

## How to read this book

One page per component. Each page says what the component exposes, what it depends on, how it behaves, what it guarantees, and how it fails. Decisions are dated. Anything marked `<!-- inferred — verify -->` was read from code, not confirmed by a person.
