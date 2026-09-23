"""`create_app()` must boot with no arguments and no environment, because that
is how `uvicorn --factory` calls it."""

import httpx


async def test_app_boots_and_describes_itself(running: httpx.AsyncClient) -> None:
    response = await running.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "Experience API"
