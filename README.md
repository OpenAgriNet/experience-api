# experience-api

The Experience API sits between the OpenAgriNet web client and the Decision
Support System (DSS). The client sends a chat turn; the API builds a DSS
request, calls the DSS, and streams the answer back.

## Run it

Needs [uv](https://docs.astral.sh/uv/). It installs Python 3.13 itself.

```bash
uv sync
uv run uvicorn --factory experience_api.app:create_app --port 8078
```

The API listens on `http://localhost:8078`.

| Path | What |
|---|---|
| `POST /v1/chat` | One chat turn, [contract](./docs/api-contracts/api-contract.md) §4–§6 |
| `GET /healthz` | `{"status": "ok"}` when the process is up. For Docker and the proxy |
| `GET /docs` | The interactive OpenAPI page |

By default a fake DSS answers every turn, so the API runs with nothing else
installed. To call a real one:

```bash
EXPERIENCE_API_DSS_MODE=http uv run uvicorn --factory experience_api.app:create_app --port 8078
```

| Variable | Default | What |
|---|---|---|
| `EXPERIENCE_API_DSS_MODE` | `fake` | `fake`, or `http` to call the DSS |
| `EXPERIENCE_API_DSS_BASE_URL` | `http://localhost:8077` | Where the DSS listens |
| `EXPERIENCE_API_CHANNEL` | `web` | Sent to the DSS as the channel |
| `EXPERIENCE_API_MAX_CHARACTERS` | `1200` | The longest answer to ask the DSS for |

A bad value stops the API from starting. Errors from the DSS itself (it being
down, busy, or refusing the request) come back as a plain `500` for now.

```bash
curl -i http://localhost:8078/healthz
```

Add `--reload` to restart on every file change while developing.

### With Docker

```bash
docker compose up --build        # add -d to run it in the background
docker compose down
```

Same port, same fake DSS. `EXPERIENCE_API_DSS_MODE=http docker compose up
--build` calls a DSS on the host's port 8077; the other variables pass through
too. Set `EXPERIENCE_API_HOST_PORT` to publish on another port. The container
reports healthy once `/healthz` answers.

### Try a chat turn

```bash
cat > request.json <<'JSON'
{
  "sessionId": "68a3872f-3f0d-4cf6-99a3-a350132a0080",
  "messageId": "1ab38d6c-6fdb-4849-8ea1-da5e80a8687c",
  "query": "And what about tomorrow?",
  "history": [],
  "language": { "source": "en", "target": "en" }
}
JSON

# Streamed: started, delta..., completed
curl -N -H 'Accept: text/event-stream' -H 'Content-Type: application/json' \
     -d @request.json http://localhost:8078/v1/chat

# One JSON answer
curl -H 'Content-Type: application/json' -d @request.json http://localhost:8078/v1/chat
```

A body that breaks the contract's rules gets FastAPI's default `422` for now
(contract §6.1).

## Check it

```bash
uv run ruff check . && uv run ruff format --check .   # lint, format
uv run pyright                                        # types
uv run vulture                                        # dead code
uv run pytest                                         # tests, with coverage
```

Once per clone, install the git hooks. Lint, types and dead code run on every
commit; the test suite runs before every push. CI runs the same checks, so
`--no-verify` only moves a failure later.

```bash
uv run pre-commit install --hook-type pre-commit --hook-type pre-push
```

## Docs

- [`docs/api-contracts/api-contract.md`](./docs/api-contracts/api-contract.md): the contract the web client builds against
- [`docs/ADR/`](./docs/ADR): accepted decisions; ADR-0001 is the architecture
- [`CLAUDE.md`](./CLAUDE.md): layout, stack, test tiers
- [`CONVENTIONS.md`](./CONVENTIONS.md): naming, commits, PRs
