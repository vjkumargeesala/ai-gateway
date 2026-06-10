import json
import logging
import re
import sys
from contextvars import ContextVar
from datetime import datetime, timezone

# Request ID accessible from anywhere in the current async context
request_id_var: ContextVar[str] = ContextVar("request_id", default="startup")
user_id_var: ContextVar[str] = ContextVar("user_id", default="anonymous")


# ─── PII Redaction ──────────────────────────────────────────────────────────

# Patterns: email, US phone (any common format), credit card numbers
PII_PATTERNS = [
    (re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"), "[REDACTED_EMAIL]"),
    (
        re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
        "[REDACTED_PHONE]",
    ),
    (re.compile(r"\b(?:\d[ -]*?){13,16}\b"), "[REDACTED_CARD]"),
]


def redact_pii(text: str) -> str:
    """Replace emails, phone numbers, and credit card numbers in text."""
    if not isinstance(text, str):
        return text
    for pattern, replacement in PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


# ─── JSON Formatter ─────────────────────────────────────────────────────────


class JSONFormatter(logging.Formatter):
    """Format every log line as JSON with PII redaction on string values."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "request_id": request_id_var.get(),
            "user_id": user_id_var.get(),
        }

        if hasattr(record, "extra_fields"):
            for key, value in record.extra_fields.items():  # type: ignore
                log_entry[key] = redact_pii(value) if isinstance(value, str) else value

        return json.dumps(log_entry)


def setup_logging(log_level: str = "INFO") -> None:
    """Configure structured JSON logging for the whole app."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    root = logging.getLogger()
    root.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    root.handlers.clear()
    root.addHandler(handler)
