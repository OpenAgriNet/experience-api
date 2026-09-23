# experience-api

The Experience API sits between the OpenAgriNet web client and the Decision
Support System (DSS). The client sends a chat turn; the API builds a DSS
request, calls the DSS, and streams the answer back.

## Run it

```bash
uv sync
uv run ruff check . && uv run ruff format --check . && uv run pytest
```
