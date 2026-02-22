"""
Dead Code Hygiene Tests — verify unused imports are removed and
deprecated shims are not used by new code.
"""
import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _get_imported_names(filepath: Path) -> set[str]:
    """Parse a Python file and return all imported names."""
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.asname or alias.name)
    return names


def _get_used_names(filepath: Path) -> set[str]:
    """Parse a Python file and return all Name references (excluding imports)."""
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            # Catch things like RepoDirtyError in type annotations
            if isinstance(node.value, ast.Name):
                names.add(node.value.id)
    return names


class TestNoUnusedImports:
    """Verify key files don't have unused imports."""

    def test_autonomous_build_cycle_no_unused(self):
        """autonomous_build_cycle.py should not import unused symbols."""
        path = REPO_ROOT / "runtime/orchestration/missions/autonomous_build_cycle.py"
        imported = _get_imported_names(path)
        used = _get_used_names(path)
        # These specific symbols were identified as unused
        for name in [
            "select_eligible_item",
            "BacklogPriority",
            "TaskPriority",
            "verify_repo_clean",
            "run_git_command",
            "FileLock",
        ]:
            assert not (name in imported and name not in used), (
                f"'{name}' is imported but never used in "
                "autonomous_build_cycle.py"
            )

    def test_spine_no_unused(self):
        """spine.py should not import unused symbols."""
        path = REPO_ROOT / "runtime/orchestration/loop/spine.py"
        imported = _get_imported_names(path)
        used = _get_used_names(path)
        for name in [
            "RepoDirtyError",
            "LedgerIntegrityError",
            "TerminalOutcome",
            "TerminalReason",
            "HookSequenceResult",
        ]:
            assert not (name in imported and name not in used), (
                f"'{name}' is imported but never used in spine.py"
            )


class TestNoDeprecatedShimUsage:
    """Verify test files use canonical imports, not deprecated shims."""

    def test_agent_api_uses_canonical_logging(self):
        """test_agent_api.py should import from runtime.agents.logging, not agent_logging."""
        path = REPO_ROOT / "runtime/tests/test_agent_api.py"
        source = path.read_text(encoding="utf-8")
        assert "agent_logging" not in source, (
            "test_agent_api.py still imports from deprecated agent_logging shim. "
            "Change to: from runtime.agents.logging import ..."
        )

    def test_opencode_stage1_uses_canonical_logging(self):
        """test_opencode_stage1.py should import from runtime.agents.logging."""
        path = REPO_ROOT / "runtime/tests/test_opencode_stage1.py"
        source = path.read_text(encoding="utf-8")
        assert "agent_logging" not in source, (
            "test_opencode_stage1.py still imports from deprecated agent_logging shim. "
            "Change to: from runtime.agents.logging import ..."
        )


class TestNoOrphanedFiles:
    """Verify orphaned files have been cleaned up."""

    def test_no_disabled_ci_runner(self):
        """opencode_ci_runner.py.DISABLED should not exist."""
        path = REPO_ROOT / "scripts/opencode_ci_runner.py.DISABLED"
        assert not path.exists(), (
            "scripts/opencode_ci_runner.py.DISABLED still exists. Remove it (git rm)."
        )
