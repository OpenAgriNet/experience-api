"""Settings come from `EXPERIENCE_API_*` environment variables, then `.env`."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from experience_api.settings import Settings


def _from_env() -> Settings:
    """`Settings` as `app.py` builds it: from the environment and `.env` only."""

    return Settings()  # pyright: ignore[reportCallIssue]


def test_defaults_run_against_the_fake_dss(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("DSS_MODE", "DSS_BASE_URL", "CHANNEL", "MAX_CHARACTERS"):
        monkeypatch.delenv(f"EXPERIENCE_API_{name}", raising=False)

    settings = _from_env()

    assert settings.dss_mode == "fake"
    assert settings.dss_base_url == "http://localhost:8077"
    assert settings.channel == "web"
    assert settings.max_characters == 1200


def test_read_from_the_prefixed_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXPERIENCE_API_DSS_MODE", "http")
    monkeypatch.setenv("EXPERIENCE_API_DSS_BASE_URL", "http://dss:8077")
    monkeypatch.setenv("EXPERIENCE_API_MAX_CHARACTERS", "600")

    settings = _from_env()

    assert (settings.dss_mode, settings.dss_base_url, settings.max_characters) == (
        "http",
        "http://dss:8077",
        600,
    )


@pytest.mark.parametrize(
    ("name", "value"),
    [("DSS_MODE", "real"), ("MAX_CHARACTERS", "0")],
)
def test_a_bad_value_stops_the_app_from_starting(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str
) -> None:
    monkeypatch.setenv(f"EXPERIENCE_API_{name}", value)

    with pytest.raises(ValidationError):
        _from_env()


@pytest.mark.parametrize("value", [None, "", "   "])
def test_a_missing_or_blank_sender_id_stops_the_app(
    monkeypatch: pytest.MonkeyPatch, value: str | None
) -> None:
    if value is None:
        monkeypatch.delenv("EXPERIENCE_API_SENDER_ID")
    else:
        monkeypatch.setenv("EXPERIENCE_API_SENDER_ID", value)

    with pytest.raises(ValidationError, match="sender_id"):
        _from_env()


def test_the_sender_id_comes_from_dot_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("EXPERIENCE_API_SENDER_ID")
    env_file = tmp_path / ".env"
    env_file.write_text("EXPERIENCE_API_SENDER_ID=experience-api.local\n")
    monkeypatch.setitem(Settings.model_config, "env_file", env_file)

    assert _from_env().sender_id == "experience-api.local"


def test_the_environment_wins_over_dot_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("EXPERIENCE_API_SENDER_ID", "exp-from-env")
    env_file = tmp_path / ".env"
    env_file.write_text("EXPERIENCE_API_SENDER_ID=experience-api.local\n")
    monkeypatch.setitem(Settings.model_config, "env_file", env_file)

    assert _from_env().sender_id == "exp-from-env"


def test_a_dot_env_key_that_is_not_a_setting_is_ignored(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Compose reads `EXPERIENCE_API_HOST_PORT` from the same `.env`.
    env_file = tmp_path / ".env"
    env_file.write_text("EXPERIENCE_API_HOST_PORT=9000\n")
    monkeypatch.setitem(Settings.model_config, "env_file", env_file)

    assert _from_env().sender_id
