"""Stub LLMProvider for testing the orchestration layer.

All tests in test_orchestration use this provider — no real model key
is needed to pass Phase 5's acceptance criteria.
"""

from __future__ import annotations

import asyncio
from typing import Any

from pydantic import BaseModel

from backend.orchestration.adapter import build_tool_definition, extract_tool_call


class StubProvider:
    """Parameterizable stub implementing ``LLMProvider``.

    Configure with either *result* (a dict the stub returns) or *error*
    (an exception it raises).  The stub simulates the full adapter pipeline:
    tool-def construction, forced tool_choice, extraction, and model_validate.

    For timeout simulation, set *error* to ``asyncio.TimeoutError``
    (which ``complete_structured`` translates to the expected behavior).
    """

    def __init__(
        self,
        *,
        result: dict[str, Any] | None = None,
        error: Exception | None = None,
        delay_s: float = 0.0,
        tier: str = "stub",
    ) -> None:
        self._result = result
        self._error = error
        self._delay_s = delay_s
        self._tier = tier

    async def complete_structured(
        self,
        *,
        system: str,  # noqa: ARG002
        user: str,  # noqa: ARG002
        schema: type[BaseModel],
        timeout_s: float,  # noqa: ARG002
    ) -> BaseModel:
        if self._delay_s > 0:
            await asyncio.sleep(self._delay_s)

        if self._error is not None:
            raise self._error

        # Build tool definition and extract — simulates the adapter path
        tool_def = build_tool_definition(schema)
        tool_name = tool_def["name"]

        if self._result is not None:
            response: dict[str, Any] = {
                "content": [
                    {"type": "tool_use", "name": tool_name, "input": self._result},
                ],
            }
            args = extract_tool_call(response, tool_name)
        else:
            # No result configured — return a default-constructed instance
            return schema()

        return schema.model_validate(args)

    async def complete_text(
        self,
        *,
        system: str,  # noqa: ARG002
        user: str,  # noqa: ARG002
        timeout_s: float,  # noqa: ARG002
    ) -> str:
        if self._delay_s > 0:
            await asyncio.sleep(self._delay_s)
        if self._error is not None:
            raise self._error
        return str(self._result) if self._result is not None else ""
