"""`GET /healthz` is for whoever runs the service, such as Docker or the front
proxy. It is not for the client, so it is not in the contract."""

import httpx


async def test_healthz_says_ok(running: httpx.AsyncClient) -> None:
    response = await running.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_healthz_is_not_in_the_openapi_document(
    running: httpx.AsyncClient,
) -> None:
    paths = (await running.get("/openapi.json")).json()["paths"]

    assert "/healthz" not in paths
