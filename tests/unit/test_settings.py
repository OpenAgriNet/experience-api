"""Settings come from `EXPERIENCE_API_*` environment variables."""

import pytest
from pydantic import ValidationError

from experience_api.settings import Settings


def test_defaults_run_against_the_fake_dss(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("DSS_MODE", "DSS_BASE_URL", "CHANNEL", "MAX_CHARACTERS"):
        monkeypatch.delenv(f"EXPERIENCE_API_{name}", raising=False)

    settings = Settings()

    assert settings.dss_mode == "fake"
    assert settings.dss_base_url == "http://localhost:8077"
    assert settings.channel == "web"
    assert settings.max_characters == 1200


def test_read_from_the_prefixed_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXPERIENCE_API_DSS_MODE", "http")
    monkeypatch.setenv("EXPERIENCE_API_DSS_BASE_URL", "http://dss:8077")
    monkeypatch.setenv("EXPERIENCE_API_MAX_CHARACTERS", "600")

    settings = Settings()

    assert (settings.dss_mode, settings.dss_base_url, settings.max_characters) == (
        "http",
        "http://dss:8077",
        600,
    )


@pytest.mark.parametrize(
    ("name", "value"),
    [("DSS_MODE", "real"), ("MAX_CHARACTERS", "0"), ("CHANNEL", "email")],
)
def test_a_bad_value_stops_the_app_from_starting(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str
) -> None:
    monkeypatch.setenv(f"EXPERIENCE_API_{name}", value)

    with pytest.raises(ValidationError):
        Settings()
