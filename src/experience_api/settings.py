"""Configuration, from `EXPERIENCE_API_*` environment variables.

Read only by `app.py`, which hands services plain values. A bad mode, channel
or length stops the app from starting. The DSS URL is not checked here: a wrong
one fails like an unreachable DSS, on the first turn.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EXPERIENCE_API_")

    # `fake` answers every turn from memory; `http` calls the DSS.
    dss_mode: Literal["fake", "http"] = "fake"
    dss_base_url: str = "http://localhost:8077"
    # Sent to the DSS as `attributes.channel` and `response.maxCharacters`
    # (contract §7). The channels are the DSS's own set.
    channel: Literal["web", "whatsapp", "voice", "sms"] = "web"
    max_characters: int = Field(default=1200, ge=1)
