"""Cursor pagination utilities.

Doc #5 §1.5 — cursor-param pagination for list/feed endpoints.
"""

from __future__ import annotations

import base64
import json
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class CursorPage(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None = None
    has_more: bool = False


def encode_cursor(value: str | dict[str, str]) -> str:
    if isinstance(value, dict):
        value = json.dumps(value, sort_keys=True)
    return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")


def decode_cursor(cursor: str) -> dict[str, str]:
    padded = cursor + "=" * (4 - len(cursor) % 4) if len(cursor) % 4 else cursor
    decoded = base64.urlsafe_b64decode(padded.encode()).decode()
    result: dict[str, str] = json.loads(decoded) if decoded.startswith("{") else {"id": decoded}
    return result
