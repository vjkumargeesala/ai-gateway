import logging
import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from app.config import config
from app.api.routes import router
from app.utils.logging import setup_logging, request_id_var

# ─── Logging setup ───────────────────────────────────────────────────────────

setup_logging(config.log_level)
logger = logging.getLogger(__name__)


# ─── Lifespan: startup + graceful shutdown ───────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run code at startup and clean up at shutdown."""
    logger.info(
        "startup",
        extra={
            "extra_fields": {
                "env": config.app_env,
                "users_configured": len(config.api_keys),
                "rate_limit": config.rate_limit_per_minute,
            }
        },
    )

    yield  # Application runs while suspended here

    logger.info("shutdown_started")
    # Place to close DB connections, drain queues, flush metrics, etc.
    logger.info("shutdown_complete")


# ─── App ─────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AI Gateway",
    version="1.0.0",
    description="Production-ready REST API scaffold for wrapping LLM providers",
    lifespan=lifespan,
)


# ─── Middleware: request ID + access logging ─────────────────────────────────


@app.middleware("http")
async def attach_request_id(request: Request, call_next):
    """Generate a request ID, log access, set X-Request-ID header."""
    rid = str(uuid.uuid4())[:8]
    request_id_var.set(rid)

    start = time.time()
    response = await call_next(request)
    latency_ms = round((time.time() - start) * 1000, 2)

    logger.info(
        "http_request",
        extra={
            "extra_fields": {
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "latency_ms": latency_ms,
            }
        },
    )

    response.headers["X-Request-ID"] = rid
    return response


# ─── Health endpoints (no auth required) ─────────────────────────────────────


@app.get("/health", tags=["health"])
async def health():
    """Liveness probe — is the service running?"""
    return {
        "status": "healthy",
        "env": config.app_env,
        "version": "1.0.0",
    }


@app.get("/ready", tags=["health"])
async def ready():
    """Readiness probe — is the service ready to accept traffic?"""
    # In Project 1 we checked the DB connection here.
    # For a real LLM gateway you'd ping the LLM provider, check the cache, etc.
    return {"status": "ready"}


# ─── Routes ──────────────────────────────────────────────────────────────────

app.include_router(router)
