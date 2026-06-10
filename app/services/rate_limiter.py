import time
from collections import defaultdict, deque


class RateLimiter:
    """
    Per-user sliding-window rate limiter.

    For each user_id, tracks request timestamps in a deque.
    A request is allowed only if there are fewer than `max_requests`
    timestamps within the last `window_seconds`.
    """

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # user_id → deque of request timestamps
        self.requests: dict[str, deque[float]] = defaultdict(deque)

    def is_allowed(self, user_id: str) -> bool:
        """Check if user can make a request right now. Records it if allowed."""
        now = time.time()
        window_start = now - self.window_seconds
        user_requests = self.requests[user_id]

        # Drop timestamps that fall outside the current window
        while user_requests and user_requests[0] < window_start:
            user_requests.popleft()

        # Reject if user is at the cap
        if len(user_requests) >= self.max_requests:
            return False

        # Record this request and allow it
        user_requests.append(now)
        return True

    def remaining(self, user_id: str) -> int:
        """How many requests the user has left in the current window."""
        now = time.time()
        window_start = now - self.window_seconds
        user_requests = self.requests[user_id]

        while user_requests and user_requests[0] < window_start:
            user_requests.popleft()

        return max(0, self.max_requests - len(user_requests))


# Shared instance — same limiter used by every endpoint
from app.config import config
rate_limiter = RateLimiter(
    max_requests=config.rate_limit_per_minute,
    window_seconds=60,
)