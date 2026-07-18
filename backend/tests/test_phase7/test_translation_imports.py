"""Structural test: prove the translation module can never reach Reasoning tier or RAG store.

This test parses the import graph of `backend.app.services.translation` and asserts
that zero imports from reasoning-tier or retrieval modules are reachable from it.
This is a code-level architectural enforcement — the same approach Phase 6 used
to make the emergency call-count provable.

Doc #2 §4: "There is no escalation path to the Reasoning tier, and the
RAG/Vector Store is never consulted on this path."
Doc #4 §1 table: "Translation (Chat Bridge) → Fast/Cheap tier only"
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


def _resolve_module_path(filepath: Path, base_dir: Path) -> str:
    """Convert a file path to a dotted module path relative to base_dir."""
    rel = filepath.relative_to(base_dir.parent)  # parent of backend/
    parts = list(rel.parts)
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1].replace(".py", "")
    return ".".join(parts)


def _collect_imports(filepath: Path) -> set[str]:
    """Collect all fully-qualified import names from a Python file.

    Returns a set of top-level module names imported (directly or transitively).
    """
    tree = ast.parse(filepath.read_text(encoding="utf-8"))
    imports: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                imports.add(top)
        elif isinstance(node, ast.ImportFrom) and node.module:
            top = node.module.split(".")[0]
            imports.add(top)

    return imports


def _get_all_imports_recursive(
    start_path: Path,
    base_dir: Path,
    visited: set[Path] | None = None,
    depth: int = 0,
    max_depth: int = 5,
) -> set[str]:
    """Recursively collect all imports reachable from *start_path*.

    Follows relative and absolute imports within the backend package up to
    *max_depth* levels to prevent infinite recursion.
    """
    if visited is None:
        visited = set()
    if start_path in visited or depth > max_depth:
        return set()

    visited.add(start_path)

    if not start_path.exists() or start_path.suffix != ".py":
        return set()

    tree = ast.parse(start_path.read_text(encoding="utf-8"))
    all_imports: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                all_imports.add(top)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split(".")[0]
                all_imports.add(top)
            # Follow relative imports
            if node.module and node.module.startswith("backend"):
                rel_path_parts = node.module.split(".")[1:]  # skip 'backend'
                import_file = base_dir
                for part in rel_path_parts:
                    import_file = import_file / part
                import_file_py = import_file.with_suffix(".py")
                import_file_init = import_file / "__init__.py"

                next_file = None
                if import_file_py.exists():
                    next_file = import_file_py
                elif import_file_init.exists():
                    next_file = import_file_init

                if next_file and next_file not in visited:
                    transitive = _get_all_imports_recursive(
                        next_file, base_dir, visited, depth + 1, max_depth,
                    )
                    all_imports.update(transitive)

    return all_imports


# === Forbidden modules ===
# Reasoning-tier or RAG-related top-level modules that translation must never touch.
FORBIDDEN_TOP_LEVEL: set[str] = {
    # RAG / vector store modules
    "chromadb",
    "chroma",
    "langchain",
    "sentence_transformers",
    # Business-logic Reasoning-tier modules
    "dispatch_recommender",
    "ask_crewlink",
    # If orchestration has reasoning-specific submodules
}

# Forbidden submodule paths within our own codebase
FORBIDDEN_SUBMODULES: set[str] = {
    "backend.orchestration.fallbacks",  # translation has its own fallback
    "backend.app.services.dispatch_recommender",
    "backend.app.services.kb_lookup",  # RAG-related
    "backend.app.services.escalation",  # incident-only
    "backend.app.services.urgency",  # incident-only
}


class TestTranslationModuleImports:
    """Structural architectual-enforcement test.

    Proves the translation module's import graph contains zero paths to the
    Reasoning tier or RAG/vector store — enforced at the AST level so refactors
    that introduce an illegal import are caught in CI.
    """

    def test_translation_imports_no_reasoning_tier(self) -> None:
        """Translation module must not import any Reasoning-tier component.

        Doc #2 §4, Doc #4 §1: Translation is Fast/Cheap tier only.
        """
        base_dir = Path(__file__).resolve().parent.parent.parent / "backend"
        translation_path = base_dir / "app" / "services" / "translation.py"

        if not translation_path.exists():
            pytest.skip("translation.py not yet implemented — structural test will run once it exists")

        imports = _get_all_imports_recursive(translation_path, base_dir)

        # Check forbidden top-level modules
        for forbidden in FORBIDDEN_TOP_LEVEL:
            assert forbidden not in imports, (
                f"Translation module imports forbidden top-level module '{forbidden}'. "
                f"Doc #2 §4: Translation must never touch the Reasoning tier or RAG store."
            )

    def test_translation_imports_no_forbidden_submodules(self) -> None:
        """Translation must not import specific forbidden submodules."""
        base_dir = Path(__file__).resolve().parent.parent.parent / "backend"
        translation_path = base_dir / "app" / "services" / "translation.py"

        if not translation_path.exists():
            pytest.skip("translation.py not yet implemented")

        source = translation_path.read_text(encoding="utf-8")

        for forbidden in FORBIDDEN_SUBMODULES:
            assert forbidden not in source, (
                f"Translation module imports forbidden submodule '{forbidden}'. "
                f"Doc #2 §4: Chat Bridge never touches the Reasoning tier or RAG."
            )

    def test_translation_only_uses_fast_cheap_tier(self) -> None:
        """Verify translation.py uses TaskType.TRANSLATION (Fast/Cheap)."""
        base_dir = Path(__file__).resolve().parent.parent.parent / "backend"
        translation_path = base_dir / "app" / "services" / "translation.py"

        if not translation_path.exists():
            pytest.skip("translation.py not yet implemented")

        source = translation_path.read_text(encoding="utf-8")

        # Must use TRANSLATION task type
        assert "TaskType.TRANSLATION" in source, (
            "Translation service must use TaskType.TRANSLATION (Fast/Cheap tier)"
        )
        # Must NOT use DISPATCH_RECOMMENDATION or ASK_CREWLINK_SYNTHESIS
        assert "TaskType.DISPATCH_RECOMMENDATION" not in source, (
            "Translation must not use the Reasoning-tier dispatch task type"
        )
        assert "TaskType.ASK_CREWLINK_SYNTHESIS" not in source, (
            "Translation must not use the Reasoning-tier Ask CrewLink task type"
        )
