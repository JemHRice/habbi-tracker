"""The error envelope, and the mapping from domain refusals onto HTTP.

Every error the API returns looks the same:

    {"error": {"code": "EDIT_WINDOW_LOCKED", "message": "..."}}

The domain layer knows nothing about HTTP; it raises
:class:`~app.domain.errors.DomainError` subclasses, and this module is the one
place that decides what each becomes on the wire.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.domain.errors import (
    DateOutOfRange,
    DomainError,
    EditWindowClosed,
    HabitAlreadyScheduled,
    HabitInactive,
    HabitNotOwned,
    HabitNotScheduled,
    InvalidPin,
    NotFound,
)
from app.domain.habits import InvalidSchedule

UNAUTHENTICATED = "UNAUTHENTICATED"
PIN_INVALID = "PIN_INVALID"
PIN_THROTTLED = "PIN_THROTTLED"
EDIT_WINDOW_LOCKED = "EDIT_WINDOW_LOCKED"
NOT_FOUND = "NOT_FOUND"
VALIDATION = "VALIDATION"


class ApiError(Exception):
    """An error raised by the transport layer itself (auth, throttling)."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


DOMAIN_ERROR_MAP: dict[type[DomainError], tuple[int, str]] = {
    EditWindowClosed: (403, EDIT_WINDOW_LOCKED),
    NotFound: (404, NOT_FOUND),
    HabitNotOwned: (404, NOT_FOUND),
    HabitInactive: (400, VALIDATION),
    HabitNotScheduled: (400, VALIDATION),
    HabitAlreadyScheduled: (400, VALIDATION),
    InvalidSchedule: (400, VALIDATION),
    InvalidPin: (400, VALIDATION),
    DateOutOfRange: (400, VALIDATION),
}
"""How each domain refusal is reported.

`HabitNotOwned` deliberately becomes a 404 rather than a 403: telling one board
that a habit exists but belongs to the other board is itself a leak.
"""


def envelope(status_code: int, code: str, message: str) -> JSONResponse:
    """Build the standard error response body."""
    return JSONResponse(
        status_code=status_code, content={"error": {"code": code, "message": message}}
    )


def classify(error: DomainError) -> tuple[int, str]:
    """Return the status and code for a domain error, walking its ancestry.

    Subclasses inherit their parent's mapping, so a new error type is reported
    sensibly even before it is listed explicitly.
    """
    for error_type in type(error).__mro__:
        if error_type in DOMAIN_ERROR_MAP:
            return DOMAIN_ERROR_MAP[error_type]
    return 400, VALIDATION


def register_exception_handlers(app: FastAPI) -> None:
    """Attach the handlers that keep every error in the same envelope."""

    @app.exception_handler(ApiError)
    async def _api_error(_request: Request, error: ApiError) -> JSONResponse:
        return envelope(error.status_code, error.code, error.message)

    @app.exception_handler(DomainError)
    async def _domain_error(_request: Request, error: DomainError) -> JSONResponse:
        status_code, code = classify(error)
        return envelope(status_code, code, str(error))

    @app.exception_handler(RequestValidationError)
    async def _validation_error(
        _request: Request, error: RequestValidationError
    ) -> JSONResponse:
        detail = error.errors()
        message = "Request validation failed"
        if detail:
            first = detail[0]
            location = ".".join(str(part) for part in first.get("loc", ()) if part != "body")
            message = f"{location}: {first.get('msg', message)}" if location else str(
                first.get("msg", message)
            )
        return envelope(422, VALIDATION, message)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(
        _request: Request, error: StarletteHTTPException
    ) -> JSONResponse:
        code = {
            401: UNAUTHENTICATED,
            403: EDIT_WINDOW_LOCKED,
            404: NOT_FOUND,
            422: VALIDATION,
        }.get(error.status_code, VALIDATION)
        return envelope(error.status_code, code, str(error.detail))
