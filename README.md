# experience-api

The Experience API sits between the OpenAgriNet web client and the Decision
Support System (DSS). The client sends a chat turn; the API builds a DSS
request, calls the DSS, and streams the answer back.

## Run it

```bash
uv sync
uv run ruff check . && uv run ruff format --check . && uv run pytest
```

Once per clone, install the git hooks. Lint runs on every commit; the test
suite runs before every push. CI runs the same checks, so `--no-verify` only
moves a failure later.

```bash
uv run pre-commit install --hook-type pre-commit --hook-type pre-push
```
