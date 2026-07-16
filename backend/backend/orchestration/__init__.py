"""CrewLink AI — AI Orchestration Layer

Doc #4: AI/LLM Orchestration & Prompt Design
Everything in this package implements Doc #4's tiering, enforcement pipeline,
structured-output schemas, fallback table, and AIInvocationLog instrumentation.

No vendor SDK or model name is imported anywhere outside this package.
"""

from .completion import CompletionResult, complete_with_fallback
from .fallbacks import FALLBACK_MAP, FallbackRegistry
from .interfaces import TASK_TIER_MAP, ModelRouter, ModelTier, TaskType

__all__ = [
    "ModelTier",
    "ModelRouter",
    "TaskType",
    "TASK_TIER_MAP",
    "CompletionResult",
    "complete_with_fallback",
    "FALLBACK_MAP",
    "FallbackRegistry",
]
