# experience-api

## Service overview
The Experience API sits between the OpenAgriNet web client and the Decision
Support System (DSS). The client sends a chat turn; the API checks it, builds a
DSS `/v1/turns` request, and streams the answer back in the client's shape. It
stores nothing.

## Architecture and contract
Do not repeat architecture or contract detail here; it goes stale. The sources:
- **`docs/api-contracts/api-contract.md`**: what the API does on the wire. §3–§7
  bind this repo. The web client builds against the same file, so a change is
  made there first, then in code.
- **`docs/ADR/`**: accepted decisions. ADR-0001 is the architecture: features at
  the top, ports and adapters inside each feature.

## Tech stack
- Python 3.13, FastAPI on uvicorn (ADR-0001).
- httpx and httpx-sse for the DSS call; pydantic-settings for config, env prefix
  `EXPERIENCE_API_`.
- uv, ruff, pyright, vulture, pytest, pre-commit.

## Build and run
Install: `uv sync`, then `uv run pre-commit install --hook-type pre-commit --hook-type pre-push`
Check: `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run vulture && uv run pytest`
Run: `uv run uvicorn --factory experience_api.app:create_app --port 8078`

## Domain language
The full shapes live in `chat/domain.py`. The words to know:
- **Turn** (`ChatTurn`): one user message plus the history before it.
- **Answer**: outcome, content blocks (text or refusal), sources, optional error.
- **Citation**: points a source at a span of a text block (code-point offsets).
- **Events**: the DSS yields `DssStarted`, `DssDelta`, `DssFinished`; the service
  yields `Started`, `Delta`, `Completed`. `Completed` is the authoritative
  answer; it replaces what the deltas built up.
- **Trace id**: the DSS's name for one attempt; the client shows it on failure.

## What this service provides
- `POST /v1/chat`: one chat turn. `Accept: text/event-stream` streams it;
  anything else returns one JSON answer. Contract §4–§5.
- `GET /healthz`: the process is up. It does not probe the DSS.

## What this service depends on
- **DSS**, `POST /v1/turns` over SSE, at `EXPERIENCE_API_DSS_BASE_URL`.
  `EXPERIENCE_API_DSS_MODE=fake` (the default) answers from memory instead.
- No database, no messaging.

## Conventions
Naming, commits, PRs, logging and linting are in [`CONVENTIONS.md`](./CONVENTIONS.md).
Read it before naming anything or writing a commit.

## Writing style
For ADRs, PR descriptions, comments and docs: simple words, short sentences,
nothing that is not needed. Write for a reader without a software background.

## Folder structure
Features at the top; each keeps its own layers. `tests/test_boundaries.py`
enforces who may import what (ADR-0001 §4.1).

```
src/experience_api/
├── app.py            # create_app() and lifespan: the composition root; the only reader of Settings
├── settings.py       # pydantic-settings; each setting arrives with its first reader
├── shared/           # cross-cutting only: the Error body
└── <feature>/        # chat/ today
    ├── domain.py     # plain types and errors; stdlib and pydantic only
    ├── service.py    # the feature's rules; takes config as plain values
    ├── ports.py      # Protocols for what the feature needs from outside
    └── adapters/
        ├── http/     # inbound: routes, wire schemas (camelCase), mapping
        └── <name>/   # outbound: implements a port (dss/ today, with a fake)
```

## Testing
TDD: write the failing test first. Every commit is green.

| Tier | Path | What | Uses |
|---|---|---|---|
| Unit | `tests/unit/<feature>/` | mapping, the service, SSE framing | the fake DSS; fixed clock and ids |
| API | `tests/api/` | the whole app through httpx's ASGI transport | the fake DSS |
| Integration | `tests/integration/` | `HttpDssClient` against a local HTTP server | pytest-httpserver |
| E2E | `tests/e2e/` | one turn against a real DSS | marker `e2e`, not run by default |
| Boundaries | `tests/test_boundaries.py` | the dependency rule | the AST |

## Known gotchas
- httpx's ASGI transport does not run lifespan events. Use the `running`
  fixture in `tests/conftest.py`, which does.
- vulture cannot see a route FastAPI calls. Route decorators are ignored in
  `pyproject.toml`; any other false positive goes in `vulture_whitelist.py`.
- Imports are absolute only (ruff bans relative ones). A relative import hides
  which layer it reaches into.
- A DSS stream that ends before `DssFinished` is not handled yet
  (`TODO(phase 4)` in `chat/service.py`).

## Component specs

Behaviour and guarantees per component live in `docs/spec/` (start at `docs/spec/README.md`). Before starting new work, if `docs/.agent/specs/` has story specs, run `/update-component-spec` to fold them in.
