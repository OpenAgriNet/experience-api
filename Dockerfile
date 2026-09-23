# syntax=docker/dockerfile:1
FROM python:3.13-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /uvx /usr/local/bin/

# The image's own Python, never one uv downloads; runtime dependencies only.
ENV UV_PYTHON_DOWNLOADS=never \
    UV_NO_DEV=1

# Dependencies before source, so a code change does not reinstall them.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# README.md is package metadata; the build fails without it.
COPY README.md ./
COPY src/ ./src/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

# Fail the build, not the first request, if the app cannot be imported.
RUN python -c "import experience_api.app"

# Nothing here needs root.
RUN useradd --system --no-create-home app
USER app

EXPOSE 8078

CMD ["uvicorn", "--factory", "experience_api.app:create_app", "--host", "0.0.0.0", "--port", "8078"]
