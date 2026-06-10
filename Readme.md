# AI Gateway

A production-ready REST API scaffold for wrapping LLM providers (Claude, OpenAI, Bedrock).

This is **Project 3** of the Applied GenAI / LLM Engineer track — a foundational AI service with auth, rate limiting, retries, PII-safe logging, and observability. The LLM is currently mocked; real providers plug in cleanly in Module 4.

## Status

In active development. See progress in commit history.

## Setup

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

## License

MIT