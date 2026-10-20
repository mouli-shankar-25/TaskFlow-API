from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.logging import get_logger, setup_logging
from app.db.session import engine

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("TaskFlow API starting up (env=%s)", settings.APP_ENV)
    yield
    await engine.dispose()
    logger.info("TaskFlow API shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="TaskFlow API",
        description=(
            "A secure, maintainable Task Management REST API. "
            "Manage projects, memberships, and tasks with role-based authorization."
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # Routes
    app.include_router(api_v1_router)

    @app.get("/", include_in_schema=False)
    async def root():
        return RedirectResponse(url="/docs")

    @app.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "healthy", "version": "1.0.0"}

    @app.get("/ready", tags=["Health"])
    async def readiness_check():
        from app.db.init import check_db_connection
        from app.db.session import async_session_factory

        async with async_session_factory() as session:
            db_ok = await check_db_connection(session)
        return {
            "status": "ready" if db_ok else "not_ready",
            "database": "connected" if db_ok else "disconnected",
        }

    return app


app = create_app()
