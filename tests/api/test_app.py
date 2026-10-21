"""`create_app()` must boot with no arguments and no environment, because that
is how `uvicorn --factory` calls it."""

import httpx
import pytest

from experience_api.app import create_app
from experience_api.settings import Settings


async def test_app_boots_and_describes_itself(running: httpx.AsyncClient) -> None:
    response = await running.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "Experience API"


@pytest.mark.parametrize("channel", ["voice", "email", "WEB"])
def test_a_default_channel_outside_the_enum_stops_the_app(channel: str) -> None:
    with pytest.raises(ValueError, match=channel):
        create_app(Settings(channel=channel))
