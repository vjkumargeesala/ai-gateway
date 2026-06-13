import json
import logging
import pytest
from fastapi.testclient import TestClient

# ─── Health endpoints (no auth) ──────────────────────────────────────────────


def test_health_returns_healthy(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_ready_returns_ready(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


# ─── Authentication ──────────────────────────────────────────────────────────


def test_missing_api_key_returns_403(client):
    response = client.post(
        "/api/v1/completions",
        json={"prompt": "hello"},
    )
    assert response.status_code == 403


def test_wrong_api_key_returns_401(client):
    response = client.post(
        "/api/v1/completions",
        headers={"X-API-Key": "totally-wrong"},
        json={"prompt": "hello"},
    )
    assert response.status_code == 401


def test_valid_api_key_returns_200(client, alice_headers):
    response = client.post(
        "/api/v1/completions",
        headers=alice_headers,
        json={"prompt": "hello"},
    )
    assert response.status_code == 200


# ─── Validation ──────────────────────────────────────────────────────────────


def test_empty_prompt_rejected(client, alice_headers):
    response = client.post(
        "/api/v1/completions",
        headers=alice_headers,
        json={"prompt": ""},
    )
    assert response.status_code == 422


def test_missing_prompt_rejected(client, alice_headers):
    response = client.post(
        "/api/v1/completions",
        headers=alice_headers,
        json={},
    )
    assert response.status_code == 422


def test_prompt_too_long_rejected(client, alice_headers):
    response = client.post(
        "/api/v1/completions",
        headers=alice_headers,
        json={"prompt": "x" * 5000},
    )
    assert response.status_code == 422


def test_invalid_temperature_rejected(client, alice_headers):
    response = client.post(
        "/api/v1/completions",
        headers=alice_headers,
        json={"prompt": "hello", "temperature": 3.0},  # max is 2.0
    )
    assert response.status_code == 422


# ─── Completion response shape ───────────────────────────────────────────────


def test_completion_response_shape(client, alice_headers):
    response = client.post(
        "/api/v1/completions",
        headers=alice_headers,
        json={"prompt": "hello world"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "completion" in data
    assert "prompt_tokens" in data
    assert "completion_tokens" in data
    assert "model" in data
    assert "latency_ms" in data
    assert data["prompt_tokens"] == 2  # 'hello world' is two tokens by split()


def test_rate_limit_headers_returned(client, alice_headers):
    response = client.post(
        "/api/v1/completions",
        headers=alice_headers,
        json={"prompt": "hello"},
    )
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers


def test_request_id_in_response_header(client, alice_headers):
    response = client.post(
        "/api/v1/completions",
        headers=alice_headers,
        json={"prompt": "hello"},
    )
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) == 8


# ─── Rate limiting ───────────────────────────────────────────────────────────


def test_rate_limit_blocks_after_threshold(client, alice_headers, monkeypatch):
    """When Alice exceeds her rate limit, subsequent calls return 429."""
    from app.services import rate_limiter as rl_module

    # Force a tiny limit so we can hit it in a few requests
    monkeypatch.setattr(rl_module.rate_limiter, "max_requests", 3)

    # First 3 succeed
    for i in range(3):
        r = client.post(
            "/api/v1/completions", headers=alice_headers, json={"prompt": "x"}
        )
        assert r.status_code == 200, f"Request {i + 1} should succeed"

    # 4th is blocked
    r = client.post("/api/v1/completions", headers=alice_headers, json={"prompt": "x"})
    assert r.status_code == 429


def test_rate_limit_is_per_user(client, alice_headers, bob_headers, monkeypatch):
    """Alice running out of quota must not affect Bob."""
    from app.services import rate_limiter as rl_module

    monkeypatch.setattr(rl_module.rate_limiter, "max_requests", 2)

    # Alice uses her quota
    for _ in range(2):
        client.post("/api/v1/completions", headers=alice_headers, json={"prompt": "x"})
    blocked = client.post(
        "/api/v1/completions", headers=alice_headers, json={"prompt": "x"}
    )
    assert blocked.status_code == 429

    # Bob has his own bucket
    r = client.post("/api/v1/completions", headers=bob_headers, json={"prompt": "x"})
    assert r.status_code == 200


# ─── Retry behaviour ─────────────────────────────────────────────────────────


def test_persistent_llm_failure_returns_503(
    client, alice_headers, always_fail_llm, fast_llm
):
    """If retries exhaust, client gets 503 (not 500)."""
    response = client.post(
        "/api/v1/completions",
        headers=alice_headers,
        json={"prompt": "this will always fail"},
    )
    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"].lower()


# ─── PII redaction ───────────────────────────────────────────────────────────


def test_pii_redacted_in_logs(client, alice_headers):
    """Logs written by the JSON formatter must never contain raw PII."""
    import io
    import logging
    from app.utils.logging import JSONFormatter

    # Attach a temporary in-memory handler with the same JSONFormatter
    # the real app uses. This captures exactly what would be written to stdout.
    buffer = io.StringIO()
    handler = logging.StreamHandler(buffer)
    handler.setFormatter(JSONFormatter())
    root = logging.getLogger()
    root.addHandler(handler)

    pii_prompt = "Contact alice@example.com or 555-123-4567"

    try:
        response = client.post(
            "/api/v1/completions",
            headers=alice_headers,
            json={"prompt": pii_prompt},
        )
        assert response.status_code == 200

        log_output = buffer.getvalue()

        # Raw PII must never appear in the formatted log output
        assert "alice@example.com" not in log_output
        assert "555-123-4567" not in log_output

        # The redacted placeholders must appear
        assert "[REDACTED_EMAIL]" in log_output
        assert "[REDACTED_PHONE]" in log_output
    finally:
        root.removeHandler(handler)


# ─── OpenAPI documentation ───────────────────────────────────────────────────


def test_openapi_schema_available(client):
    """OpenAPI documentation must be auto-generated and version-pinned."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "AI Gateway"
    assert schema["info"]["version"] == "1.0.0"
    assert "/api/v1/completions" in schema["paths"]
