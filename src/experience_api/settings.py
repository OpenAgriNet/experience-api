"""Configuration, from `EXPERIENCE_API_*` environment variables, then `.env`.

`.env` is for local runs; copy `.env.example`. A real environment variable
always wins over it, and the image never carries one (`.dockerignore`).

Read only by `app.py`, which hands services plain values. A bad mode or length
stops the app from starting here; a bad channel stops it in `app.py`, which
owns the channel enum. The DSS URL is not checked: a wrong one fails like an
unreachable DSS, on the first turn.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, StringConstraints
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EXPERIENCE_API_", env_file=".env", extra="ignore"
    )

    sender_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    # `fake` answers every turn from memory; `http` calls the DSS.
    dss_mode: Literal["fake", "http"] = "fake"
    dss_base_url: str = "http://localhost:8077"
    # The channel for a turn whose client sends none (contract §4, §7). A plain
    # string: `app.py` converts it to the chat `Channel` enum at startup.
    channel: str = "web"
    max_characters: int = Field(default=1200, ge=1)
