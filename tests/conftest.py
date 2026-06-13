import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.rate_limiter import rate_limiter
from app.services.llm import llm_service
from app.config import config


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset the rate limiter before every test — tests must not pollute each other."""
    rate_limiter.requests.clear()
    yield
    rate_limiter.requests.clear()


@pytest.fixture
def client():
    """A fresh test client with a working lifespan (startup/shutdown)."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def alice_headers():
    """Auth headers for Alice — the primary test user."""
    alice_key = next(k for k, v in config.api_keys.items() if v == "alice")
    return {"X-API-Key": alice_key}


@pytest.fixture
def bob_headers():
    """Auth headers for Bob — used for per-user isolation tests."""
    bob_key = next(k for k, v in config.api_keys.items() if v == "bob")
    return {"X-API-Key": bob_key}


@pytest.fixture
def always_fail_llm(monkeypatch):
    """Force the LLM to fail 100% of the time."""
    monkeypatch.setattr(config, "llm_fail_rate", 1.0)
    yield


@pytest.fixture
def fast_llm(monkeypatch):
    """Skip the LLM latency simulation — for fast retry tests."""
    monkeypatch.setattr(config, "llm_latency_ms", 0)
    yield
