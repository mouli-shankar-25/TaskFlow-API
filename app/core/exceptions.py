import logging

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class AppException(Exception):
    def __init__(self, status_code: int, detail: str, headers: dict | None = None):
        self.status_code = status_code
        self.detail = detail
        self.headers = headers


class NotFoundError(AppException):
    def __init__(self, resource: str = "Resource"):
        super().__init__(status.HTTP_404_NOT_FOUND, f"{resource} not found")


class ForbiddenError(AppException):
    def __init__(self, detail: str = "You do not have permission to perform this action"):
        super().__init__(status.HTTP_403_FORBIDDEN, detail)


class ConflictError(AppException):
    def __init__(self, detail: str = "Resource conflict"):
        super().__init__(status.HTTP_409_CONFLICT, detail)


class BadRequestError(AppException):
    def __init__(self, detail: str = "Bad request"):
        super().__init__(status.HTTP_400_BAD_REQUEST, detail)


class UnauthorizedError(AppException):
    def __init__(self, detail: str = "Invalid credentials"):
        super().__init__(
            status.HTTP_401_UNAUTHORIZED, detail, headers={"WWW-Authenticate": "Bearer"}
        )


# Error response model for docs
class ErrorResponse(BaseModel):
    detail: str


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = []
    for error in exc.errors():
        errors.append(
            {
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
        )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation error", "errors": errors},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )
