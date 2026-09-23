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
| `GET /healthz` | `{"status": "ok"}` when the process is up. For Docker and the proxy |
| `GET /docs` | The interactive OpenAPI page |

```bash
curl -i http://localhost:8078/healthz
```

Add `--reload` to restart on every file change while developing.

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
