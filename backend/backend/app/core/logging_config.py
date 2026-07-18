"""Structured JSON logging with request_id and sensitive-field redaction.

Doc #5 §1.4 — structured logging at INFO/WARNING/ERROR with request_id.
Doc #6 §2 — sensitive-field redaction by field-name pattern.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from typing import Any

# Patterns for fields whose values should be redacted in logs.
# Matches case-insensitively against the field name.
SENSITIVE_FIELD_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"api_key", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"token", re.IGNORECASE),
    re.compile(r"password", re.IGNORECASE),
    re.compile(r"credential", re.IGNORECASE),
    re.compile(r"jwt", re.IGNORECASE),
    re.compile(r"auth.*token", re.IGNORECASE),
    re.compile(r"database_url", re.IGNORECASE),
    re.compile(r"llm.*key", re.IGNORECASE),
    re.compile(r"simulator.*auth", re.IGNORECASE),
]

REDACTED_PLACEHOLDER = "***REDACTED***"

# Context variable for request_id propagation
from contextvars import ContextVar

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    return request_id_var.get(None)


def set_request_id(rid: str) -> None:
    request_id_var.set(rid)


def _is_sensitive(key: str) -> bool:
    """Check if a field name matches any sensitive-field pattern."""
    return any(pattern.search(key) for pattern in SENSITIVE_FIELD_PATTERNS)


def _redact_value(key: str, value: Any) -> Any:
    """Redact a single value if its key is sensitive."""
    if _is_sensitive(key):
        return REDACTED_PLACEHOLDER
    if isinstance(value, dict):
        return {k: _redact_value(k, v) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_value(key, v) if isinstance(v, (dict, str)) else v for v in value]
    return value


def redact_extra(extra: dict[str, Any] | None) -> dict[str, Any] | None:
    """Recursively redact sensitive fields from an extra dict."""
    if extra is None:
        return None
    return {k: _redact_value(k, v) for k, v in extra.items()}


class JSONFormatter(logging.Formatter):
    """Plain JSON log formatter with request_id and redaction."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        rid = get_request_id()
        if rid:
            entry["request_id"] = rid

        if record.exc_info and record.exc_info[0]:
            entry["exc_info"] = self.formatException(record.exc_info)

        extra = getattr(record, "extra", None)
        if extra:
            entry["extra"] = redact_extra(extra)

        return json.dumps(entry, default=str)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    # Silence noisy libs
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
