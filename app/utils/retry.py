import asyncio
import logging
from functools import wraps
from typing import Callable, TypeVar, ParamSpec

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay_seconds: float = 1.0,
    max_delay_seconds: float = 30.0,
    retry_on: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Retry an async function on specific exceptions with exponential backoff.

    Wait pattern: 1s → 2s → 4s → 8s → ... capped at max_delay_seconds.
    On the final attempt, the exception is re-raised.

    Args:
        max_attempts: Total attempts including the first one.
        initial_delay_seconds: Wait time before the first retry.
        max_delay_seconds: Cap on the wait time between retries.
        retry_on: Tuple of exception types that should trigger a retry.
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            delay = initial_delay_seconds

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)  # type: ignore
                except retry_on as e:
                    if attempt == max_attempts:
                        logger.error(
                            "retry_exhausted",
                            extra={
                                "extra_fields": {
                                    "function": func.__name__,
                                    "attempts": attempt,
                                    "error": str(e),
                                    "error_type": type(e).__name__,
                                }
                            },
                        )
                        raise

                    wait = min(delay, max_delay_seconds)
                    logger.warning(
                        "retry_attempt",
                        extra={
                            "extra_fields": {
                                "function": func.__name__,
                                "attempt": attempt,
                                "next_wait_seconds": wait,
                                "error": str(e),
                            }
                        },
                    )
                    await asyncio.sleep(wait)
                    delay *= 2  # Exponential growth

            # Unreachable, satisfies the type checker
            raise RuntimeError("retry loop exited without return or raise")

        return wrapper  # type: ignore

    return decorator
