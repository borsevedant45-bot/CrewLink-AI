"""Doc #4 §4 — Provider adapter: schema flattening, tool-construction, validation.

The enforcement pipeline is:
  1. ``schema.model_json_schema()`` — raw schema with ``$defs``/``$ref``.
  2. ``flatten_refs()`` — resolve ``$ref`` into inline ``$def`` definitions.
  3. Build provider-native tool/function definition from the flattened schema.
  4. Send request with ``tool_choice`` forced to that one tool — never "auto".
  5. Extract tool-call arguments from the response.
  6. Validate with ``schema.model_validate(...)``.
  7. A validation failure is a call failure (routes to fallback) — never patched.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def flatten_refs(schema: dict[str, Any]) -> dict[str, Any]:
    """Resolve ``$ref`` pointers in *schema* using its ``$defs``.

    Pydantic v2 emits enums and sub-models as ``$defs``/``$ref`` rather than
    inlining them.  Many provider tool-calling validators don't accept ``$ref``,
    so we resolve them before sending.

    This is a simplified resolver — it handles one level of ``$ref`` and
    ``allOf`` wrappers, which is sufficient for the schemas in Doc #4 §4.
    """
    result = deepcopy(schema)
    defs = result.pop("$defs", {})

    def _resolve(
        node: Any,
        _visited: set[str] | None = None,
    ) -> Any:
        if _visited is None:
            _visited = set()
        if isinstance(node, dict):
            ref = node.get("$ref", "")
            if ref and ref.startswith("#/$defs/"):
                key = ref.split("/")[-1]
                if key in _visited:
                    # Circular ref — return as-is to avoid infinite recursion
                    return node
                definition = defs.get(key)
                if definition is not None:
                    _visited.add(key)
                    return _resolve(deepcopy(definition), _visited)
            if "allOf" in node:
                # Merge allOf members (typically $ref + constraints)
                merged: dict[str, Any] = {}
                for item in node["allOf"]:
                    resolved = _resolve(item, _visited)
                    if isinstance(resolved, dict):
                        merged.update(resolved)
                # Remove merged fields and apply remaining siblings
                for k in ("allOf",):
                    node.pop(k, None)
                merged.update(node)
                return merged
            return {k: _resolve(v, _visited) for k, v in node.items()}
        if isinstance(node, list):
            return [_resolve(item, _visited) for item in node]
        return node

    return _resolve(result)  # type: ignore[no-any-return]


def build_tool_definition(
    schema: type[Any],
    *,
    flattened_schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a provider-agnostic tool/function definition from a Pydantic model.

    Returns::

        {
            "name": "ModelName",
            "description": "",
            "input_schema": { ... }   # flattened JSON Schema
        }
    """
    if flattened_schema is None:
        flattened_schema = flatten_refs(schema.model_json_schema())
    return {
        "name": schema.__name__,
        "description": "",
        "input_schema": flattened_schema,
    }


def extract_tool_call(
    response: dict[str, Any],
    tool_name: str,
) -> dict[str, Any]:
    """Extract tool-call arguments from a provider response.

    Expected *response* shape (provider-agnostic)::

        {
            "content": [
                {"type": "tool_use", "name": "...", "input": {...}},
                ...
            ]
        }

    Returns the ``input`` dict of the first tool call matching *tool_name*.
    Raises ``ValueError`` if no matching tool call is found.
    """
    content = response.get("content", [])
    for block in content:
        if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == tool_name:
                return dict(block["input"])
    msg = f"No tool_use block found for '{tool_name}' in response"
    raise ValueError(msg)
