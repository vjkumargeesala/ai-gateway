# AI Gateway

A production-ready REST API scaffold for wrapping LLM providers (Claude, OpenAI, Bedrock). Built with FastAPI, fully typed, fully tested.

This is **Another Project** of the Applied GenAI / LLM Engineer track — a foundational AI service with multi-user auth, rate limiting, retries, PII-safe logging, and observability. The LLM is currently mocked; real providers plug in cleanly in Module 4 without any other changes.

---

## Features

- **Multi-user authentication** — API keys mapped to user IDs, parsed from environment
- **Per-user rate limiting** — Sliding window, 100 req/min by default, fully independent per user
- **Automatic retries with exponential backoff** — Transient LLM failures retried with 1s, 2s, 4s waits
- **PII redaction in logs** — Emails, phone numbers, and credit cards stripped from JSON output
- **Structured JSON logging** — Every log line has a request ID and user ID for end-to-end tracing
- **Graceful shutdown** — Lifespan hooks log clean startup and termination
- **Auto-generated OpenAPI documentation** — Available at `/docs`, version-pinned
- **Health and readiness probes** — Separate `/health` (liveness) and `/ready` (readiness) endpoints
- **17 tests at 97% coverage** — Unit, integration, and behavioural tests
- **Containerised** — Single-file Dockerfile, runs as non-root, includes health check
- **CI/CD via GitHub Actions** — Lint, type-check, tests, and Docker build on every PR

---

## Requirements

- Python 3.12+
- Docker Desktop (for containerised deployment)
- Git

---

## Quick Start (Local Development)

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/ai-gateway.git
cd ai-gateway
```

### 2. Set up the environment

```bash
make setup
source venv/bin/activate
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```
APP_ENV=development
LOG_LEVEL=DEBUG
API_KEYS=dev-key-alice:alice,dev-key-bob:bob,dev-key-charlie:charlie
RATE_LIMIT_PER_MINUTE=100
LLM_FAIL_RATE=0.0
LLM_LATENCY_MS=200
```

### 4. Run the server

```bash
make dev        # With auto-reload
# or
make run        # Without reload
```

The API is now running at `http://localhost:8000`. Interactive documentation is at `http://localhost:8000/docs`.

---

## Quick Start (Docker)

```bash
make build      # Build the image
make up         # Start the container
make logs       # Tail the logs
make down       # Stop and remove
```

The API is available at `http://localhost:8000` once `make up` completes.

---

## API Endpoints

### Public Endpoints (No Authentication)

| Method | Endpoint        | Description                              |
| ------ | --------------- | ---------------------------------------- |
| GET    | `/health`       | Liveness probe — is the process alive?   |
| GET    | `/ready`        | Readiness probe — accepting traffic?     |
| GET    | `/docs`         | Interactive Swagger UI                   |
| GET    | `/openapi.json` | Raw OpenAPI specification                |

### Authenticated Endpoints

All authenticated endpoints require the `X-API-Key` header.

| Method | Endpoint                  | Description                          |
| ------ | ------------------------- | ------------------------------------ |
| POST   | `/api/v1/completions`     | Generate a completion from a prompt  |

### Example: Generate a Completion

```bash
curl -X POST http://localhost:8000/api/v1/completions \
  -H "X-API-Key: dev-key-alice" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is RAG?", "max_tokens": 100, "temperature": 0.7}'
```

**Response:**

```json
{
  "completion": "[mocked response to: 'What is RAG?...']",
  "prompt_tokens": 3,
  "completion_tokens": 6,
  "model": "mock-claude-sonnet",
  "latency_ms": 201.07
}
```

**Response Headers:**

- `X-Request-ID` — Unique 8-character ID for tracing this request through logs
- `X-RateLimit-Limit` — Maximum requests per minute for this user
- `X-RateLimit-Remaining` — Requests left in the current window

### Status Codes

| Code | Meaning                                                     |
| ---- | ----------------------------------------------------------- |
| 200  | Success                                                     |
| 401  | Invalid API key                                             |
| 403  | Missing API key                                             |
| 422  | Validation failed (empty prompt, oversized, out-of-range)   |
| 429  | Rate limit exceeded                                         |
| 503  | LLM service unavailable (all retries exhausted)             |

---

## Testing

```bash
make test           # Run all tests
make test-cov       # Run tests with coverage report
make check          # Run black + mypy + tests (everything CI runs)
```

If `make check` passes locally, CI will pass.

### Code formatting

```bash
make format         # Auto-format with black
make lint           # Check without modifying files
```

---

## Project Structure

```
ai-gateway/
├── app/
│   ├── main.py                  # FastAPI app, middleware, health endpoints
│   ├── config.py                # Configuration loaded from environment
│   ├── api/
│   │   └── routes.py            # /api/v1/completions endpoint
│   ├── services/
│   │   ├── llm.py               # Mock LLM (real provider plugs in here)
│   │   └── rate_limiter.py      # Sliding-window per-user rate limiter
│   ├── models/
│   │   └── schemas.py           # Pydantic request/response models
│   └── utils/
│       ├── logging.py           # JSON logging with PII redaction
│       └── retry.py             # Exponential backoff retry decorator
├── tests/
│   ├── conftest.py              # Shared pytest fixtures
│   └── test_routes.py           # 17 end-to-end tests
├── .github/
│   └── workflows/
│       └── test.yml             # CI workflow
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── requirements.txt             # Production dependencies
├── requirements-dev.txt         # Development + production
├── .env.example
└── README.md
```

---

## Environment Variables

| Variable                | Default          | Description                                          |
| ----------------------- | ---------------- | ---------------------------------------------------- |
| `APP_ENV`               | `development`    | Environment name                                     |
| `LOG_LEVEL`             | `INFO`           | Logging verbosity (DEBUG, INFO, WARNING, ERROR)      |
| `API_KEYS`              | _required_       | `key1:user1,key2:user2` — comma-separated mapping    |
| `RATE_LIMIT_PER_MINUTE` | `100`            | Maximum requests per minute, per user                |
| `LLM_FAIL_RATE`         | `0.0`            | Mock LLM failure probability (0.0 to 1.0)            |
| `LLM_LATENCY_MS`        | `200`            | Mock LLM simulated latency in milliseconds           |

---

## Reliability Features Explained

### Authentication

Each request must include an `X-API-Key` header. The key is looked up in a dict parsed from the `API_KEYS` environment variable:

```
API_KEYS=dev-key-alice:alice,dev-key-bob:bob
```

becomes:

```python
{"dev-key-alice": "alice", "dev-key-bob": "bob"}
```

Invalid key → 401. Missing key → 403. The validated `user_id` is then attached to every log line for the request lifecycle via a ContextVar.

### Rate Limiting

Sliding-window per-user rate limiter using a deque of timestamps. Each request:

1. Drops timestamps older than 60 seconds from the window
2. Rejects if the user has > 100 requests in the window
3. Records the timestamp and allows the request

Returns `429 Too Many Requests` when blocked. Always includes `X-RateLimit-Limit` and `X-RateLimit-Remaining` headers.

This is in-memory and per-instance — fine for a single replica. Multi-replica deployments need a shared Redis-backed limiter (Module 6 topic).

### Retry with Exponential Backoff

When the LLM throws a transient error (`LLMTimeoutError` or `LLMRateLimitError`), the retry decorator:

1. Logs a warning with the attempt number
2. Waits with exponential backoff (1s → 2s → 4s)
3. Retries up to 3 times total
4. If all attempts fail, logs `retry_exhausted` and re-raises

The endpoint catches the final exception and returns `503 Service Unavailable`. Internal details never leak to the client.

### PII Redaction

Before any string field is written to a log line, three regex patterns are applied:

- Email addresses → `[REDACTED_EMAIL]`
- US phone numbers (any common format) → `[REDACTED_PHONE]`
- Credit card numbers (13-16 digits) → `[REDACTED_CARD]`

Redaction happens in the `JSONFormatter`, so user data is captured raw in the response but masked everywhere it's logged. Adding new patterns is a one-line change in `PII_PATTERNS`.

---

## CI/CD

This project uses GitHub Actions to run quality checks on every pull request.

### What runs on each PR

1. **Black** — Code formatting check
2. **mypy** — Static type checking
3. **pytest** — Test suite with > 80% coverage gate
4. **Docker build** — Verifies the container builds cleanly

### Branch protection

The `master` branch is protected:

- Direct pushes are blocked
- All changes must go through a pull request
- CI checks must pass before merging
- Auto-delete branches on merge enabled

### Development workflow

```bash
# 1. Create a feature branch
git checkout -b feature/your-feature-name

# 2. Make changes and run checks locally
make check

# 3. Commit and push
git add .
git commit -m "Description of changes"
git push -u origin feature/your-feature-name

# 4. Open a PR on GitHub
# CI runs automatically; merge once green
```

---

## Common Commands (Makefile)

| Command           | Description                                          |
| ----------------- | ---------------------------------------------------- |
| `make help`       | List all available commands                          |
| `make setup`      | Create venv and install dependencies                 |
| `make clean`      | Remove venv, caches, build artefacts                 |
| `make run`        | Run the server (no auto-reload)                      |
| `make dev`        | Run with auto-reload                                 |
| `make test`       | Run all tests                                        |
| `make test-cov`   | Run tests with coverage report                       |
| `make check`      | Run lint + type-check + tests (everything CI runs)   |
| `make format`     | Auto-format code with black                          |
| `make lint`       | Check formatting without modifying                   |
| `make type-check` | Run mypy type checker                                |
| `make build`      | Build the Docker image                               |
| `make up`         | Start services with docker-compose                   |
| `make down`       | Stop services                                        |
| `make logs`       | Tail logs from running containers                    |

---

## Troubleshooting

### Tests pass locally but fail in CI

Check the CI environment variables — they may differ from your local `.env`. The most common cause: tests that implicitly depend on `LOG_LEVEL=DEBUG` will fail when CI sets `LOG_LEVEL=WARNING`. Tests should set their own log level rather than relying on environment config.

### Rate limit not triggering during manual testing

`uvicorn --reload` watches Python files but doesn't reload `.env` changes. Stop the server fully (`Ctrl+C`) and restart after editing `.env`.

### Docker container exits immediately

Check that `API_KEYS` is set in `docker-compose.yml`. The app raises `ValueError` at startup if it's missing — intentional, so misconfigured deployments fail loudly.

### CI not triggering on PR

The `.github/workflows/test.yml` file must exist on the feature branch, not just on `master`. Verify with:

```bash
git log --all --oneline -- .github/workflows/test.yml
```

### Mock LLM keeps failing

Check `LLM_FAIL_RATE` in your environment. Set to `0.0` for normal operation. Higher values (e.g. `0.7`) only for testing retry logic.

---

## What's Next

This service is intentionally a scaffold. The real LLM integration happens in Module 4. To swap in a real provider:

1. Replace `app/services/llm.py` with code that calls Anthropic, OpenAI, or Bedrock
2. Keep the same `complete()` method signature and `CompletionResponse` shape
3. Map provider-specific errors to `LLMTimeoutError` and `LLMRateLimitError`

Everything else — auth, rate limiting, retries, logging, observability — stays the same.

---

## Roadmap

This API is the foundation for further development as part of the Applied GenAI / LLM Engineer track:

- **Phase 1 (current)** — Production scaffold with reliability features and mock LLM
- **Phase 2 (Module 4)** — Replace mock with real LLM providers (Anthropic, OpenAI, Bedrock)
- **Phase 3 (Module 4)** — Add prompt caching, streaming responses, structured outputs
- **Phase 4 (Module 5)** — Integrate with the Document API as a RAG system
- **Phase 5 (Module 6)** — Deploy to AWS with full observability, multi-tenant cost attribution, SLOs

---

## License

MIT