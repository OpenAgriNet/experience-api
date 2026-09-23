"""Rejected bodies get FastAPI's default 422 (contract §6.1, amended). Whatever
the body held, the rejection itself must be sendable."""

import httpx

from tests.support.examples import FOLLOW_UP


async def test_a_non_finite_coordinate_is_a_422_not_a_500(
    running: httpx.AsyncClient,
) -> None:
    # Python's JSON parser reads NaN and Infinity; strict JSON cannot write them
    # back, so a rejection that echoes the input must not echo them raw.
    for bad in ("NaN", "Infinity", "1e400"):
        body = FOLLOW_UP | {"location": "PLACEHOLDER"}
        raw = httpx.Request("POST", "/", json=body).content.decode()
        raw = raw.replace('"PLACEHOLDER"', f'{{"latitude": 20, "longitude": {bad}}}')

        response = await running.post(
            "/v1/chat", content=raw, headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422, bad
        assert response.json()["detail"][0]["loc"] == ["body", "location", "longitude"]
