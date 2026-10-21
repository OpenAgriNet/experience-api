"""`create_app()` must boot with no arguments and only the sender id set,
because that is how `uvicorn --factory` calls it."""

import httpx
import pytest
from pydantic import ValidationError

from experience_api.app import create_app
from experience_api.settings import Settings
from tests.support.examples import SENDER_ID


async def test_app_boots_and_describes_itself(running: httpx.AsyncClient) -> None:
    response = await running.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "Experience API"


@pytest.mark.parametrize("channel", ["voice", "email", "WEB"])
def test_a_default_channel_outside_the_enum_stops_the_app(channel: str) -> None:
    with pytest.raises(ValueError, match=channel):
        create_app(Settings(sender_id=SENDER_ID, channel=channel))


def test_no_sender_id_stops_the_app(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EXPERIENCE_API_SENDER_ID")

    with pytest.raises(ValidationError, match="sender_id"):
        create_app()
