import logging
import time
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import APIKeyHeader
from app.config import config
from app.models.schemas import CompletionRequest, CompletionResponse
from app.services.llm import llm_service, LLMTimeoutError, LLMRateLimitError
from app.services.rate_limiter import rate_limiter
from app.utils.retry import retry_with_backoff
from app.utils.logging import request_id_var, user_id_var

router = APIRouter(prefix="/api/v1", tags=["completions"])
logger = logging.getLogger(__name__)

# ─── Authentication ──────────────────────────────────────────────────────────

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


async def authenticate(key: str = Depends(api_key_header)) -> str:
    """Validate the API key and return the associated user_id."""
    user_id = config.api_keys.get(key)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid API key")
    user_id_var.set(user_id)
    return user_id


# ─── Rate limiting ───────────────────────────────────────────────────────────


async def enforce_rate_limit(
    response: Response,
    user_id: str = Depends(authenticate),
) -> str:
    """Block the request if the user is over their rate limit."""
    if not rate_limiter.is_allowed(user_id):
        logger.warning(
            "rate_limit_exceeded",
            extra={"extra_fields": {"user_id": user_id}},
        )
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {config.rate_limit_per_minute} req/min.",
        )

    # Tell the client how many requests they have left
    response.headers["X-RateLimit-Limit"] = str(config.rate_limit_per_minute)
    response.headers["X-RateLimit-Remaining"] = str(rate_limiter.remaining(user_id))
    return user_id


# ─── LLM call with retry ─────────────────────────────────────────────────────


@retry_with_backoff(
    max_attempts=3,
    initial_delay_seconds=1.0,
    retry_on=(LLMTimeoutError, LLMRateLimitError),
)
async def call_llm_with_retry(req: CompletionRequest) -> CompletionResponse:
    """Wrapper that adds retry logic around the LLM service call."""
    return await llm_service.complete(req)


# ─── Endpoint ────────────────────────────────────────────────────────────────


@router.post("/completions", response_model=CompletionResponse)
async def create_completion(
    request: CompletionRequest,
    user_id: str = Depends(enforce_rate_limit),
) -> CompletionResponse:
    """Generate a completion from the given prompt."""
    start = time.time()

    logger.info(
        "completion_requested",
        extra={
            "extra_fields": {
                "user_id": user_id,
                "prompt": request.prompt,
                "max_tokens": request.max_tokens,
            }
        },
    )

    try:
        result = await call_llm_with_retry(request)
    except (LLMTimeoutError, LLMRateLimitError) as e:
        logger.error(
            "llm_call_failed",
            extra={
                "extra_fields": {
                    "user_id": user_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            },
        )
        raise HTTPException(
            status_code=503,
            detail="LLM service is temporarily unavailable. Please retry.",
        )

    total_latency_ms = round((time.time() - start) * 1000, 2)

    logger.info(
        "completion_succeeded",
        extra={
            "extra_fields": {
                "user_id": user_id,
                "model": result.model,
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
                "llm_latency_ms": result.latency_ms,
                "total_latency_ms": total_latency_ms,
            }
        },
    )

    return result
