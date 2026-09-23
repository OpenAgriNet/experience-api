"""Request validation failures, in FastAPI's default shape.

The first build keeps FastAPI's `422 {"detail": [...]}` (contract §6.1,
amended). This handler exists for one reason: the default echoes each bad
input back, and an input of `NaN` or `Infinity`, which Python's JSON parser
accepts, cannot be written as JSON. The default then fails with a 500. Here a
non-finite number is echoed as its string form, and nothing else changes.
"""

from __future__ import annotations

import math
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def register(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, _validation_failed)


async def _validation_failed(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    detail = _finite(jsonable_encoder(exc.errors()))
    return JSONResponse(status_code=422, content={"detail": detail})


def _finite(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {key: _finite(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_finite(item) for item in value]
    return value
