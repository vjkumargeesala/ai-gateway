from pydantic import BaseModel, Field


class CompletionRequest(BaseModel):
    """A request to generate text from a prompt."""
    prompt: str = Field(..., min_length=1, max_length=4000)
    max_tokens: int = Field(500, ge=1, le=4000)
    temperature: float = Field(0.7, ge=0.0, le=2.0)


class CompletionResponse(BaseModel):
    """The generated text response."""
    completion: str
    prompt_tokens: int
    completion_tokens: int
    model: str
    latency_ms: float


class ErrorResponse(BaseModel):
    """Standard error shape across all endpoints."""
    error: str
    detail: str | None = None
    request_id: str | None = None