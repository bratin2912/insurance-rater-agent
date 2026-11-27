import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.logging import setup_logging

settings = get_settings()

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Application startup
    logger.info("Insurance Rater Agent starting")

    yield

    # Application shutdown
    logger.info("Insurance Rater Agent shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def request_context_middleware(
    request: Request,
    call_next,
):
    request_id = str(uuid4())
    request.state.request_id = request_id

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id

    return response


@app.exception_handler(AppException)
async def handle_app_exception(
    request: Request,
    exc: AppException,
):
    request_id = getattr(request.state, "request_id", None)

    logger.warning(
        "Application error: %s",
        exc.message,
        extra={"request_id": request_id},
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "request_id": request_id,
        },
    )


@app.get("/")
async def root():
    return {
        "message": "Insurance Rater Agent API",
        "environment": settings.APP_ENV,
    }


app.include_router(
    health_router,
    prefix=settings.API_V1_PREFIX,
    tags=["Health"],
)
