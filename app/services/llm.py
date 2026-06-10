import asyncio
import random
import time
from app.config import config
from app.models.schemas import CompletionRequest, CompletionResponse


class LLMTimeoutError(Exception):
    """Raised when the LLM call times out."""
    pass


class LLMRateLimitError(Exception):
    """Raised when the LLM provider rate-limits us."""
    pass


class LLMService:
    """
    Mock LLM service. In Module 4 this gets replaced with real
    Anthropic / OpenAI / Bedrock calls — but the interface stays the same.
    """

    def __init__(self, model: str = "mock-claude-sonnet"):
        self.model = model

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Generate a completion. May fail randomly based on config."""
        start = time.time()

        # Simulate network/inference latency
        await asyncio.sleep(config.llm_latency_ms / 1000)

        # Randomly fail to simulate real-world transient errors
        if random.random() < config.llm_fail_rate:
            failure_type = random.choice([LLMTimeoutError, LLMRateLimitError])
            raise failure_type(f"Mock LLM failure: {failure_type.__name__}")

        # "Generate" a response by echoing the prompt back
        completion = f"[mocked response to: '{request.prompt[:50]}...']"

        latency_ms = (time.time() - start) * 1000

        return CompletionResponse(
            completion=completion,
            prompt_tokens=len(request.prompt.split()),
            completion_tokens=len(completion.split()),
            model=self.model,
            latency_ms=round(latency_ms, 2),
        )


# Single instance shared across the app
llm_service = LLMService()