"""
Tests for context resolver.

Per Mission Synthesis Engine MVP - P1.2
"""
import pytest
from pathlib import Path

from runtime.backlog.context_resolver import (
    resolve_context,
    ContextResolutionError,
    BASELINE_CONTEXT,
    ALLOWED_PREFIXES,
)


@pytest.fixture
def repo_with_docs(tmp_path):
    """Create a mock repo with docs structure."""
    (tmp_path / "docs" / "11_admin").mkdir(parents=True)
    (tmp_path / "docs" / "11_admin" / "LIFEOS_STATE.md").write_text("# State")
    (tmp_path / "docs" / "03_runtime").mkdir(parents=True)
    (tmp_path / "docs" / "03_runtime" / "LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md").write_text("# Arch")
    (tmp_path / "GEMINI.md").write_text("# Constitution")
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "models.yaml").write_text("# Models")
    (tmp_path / "runtime").mkdir()
    (tmp_path / "runtime" / "cli.py").write_text("# CLI")
    return tmp_path


class TestResolveContext:
    """Tests for resolve_context function."""
    
    def test_resolves_valid_hints(self, repo_with_docs):
        """Valid hints in allowlist are resolved."""
        result = resolve_context(
            task_id="TEST-001",
            context_hints=["docs/11_admin/LIFEOS_STATE.md"],
            repo_root=repo_with_docs,
        )
        assert "docs/11_admin/LIFEOS_STATE.md" in result.resolved_paths
    
    def test_includes_baseline(self, repo_with_docs):
        """Baseline context files included when they exist."""
        result = resolve_context(
            task_id="TEST-001",
            context_hints=[],
            repo_root=repo_with_docs,
        )
        assert "GEMINI.md" in result.baseline_paths
    
    def test_multiple_hints(self, repo_with_docs):
        """Multiple hints all resolved."""
        result = resolve_context(
            task_id="TEST-001",
            context_hints=[
                "docs/11_admin/LIFEOS_STATE.md",
                "config/models.yaml",
            ],
            repo_root=repo_with_docs,
        )
        assert len(result.resolved_paths) == 2
    
    def test_config_in_allowlist(self, repo_with_docs):
        """Config paths are allowed."""
        result = resolve_context(
            task_id="TEST-001",
            context_hints=["config/models.yaml"],
            repo_root=repo_with_docs,
        )
        assert "config/models.yaml" in result.resolved_paths


class TestEnvelopeValidation:
    """Tests for envelope containment validation."""
    
    def test_rejects_absolute_path(self, repo_with_docs):
        """Absolute paths rejected with ContextResolutionError."""
        # Note: Unix paths like /etc/passwd fail allowlist check first
        with pytest.raises(ContextResolutionError, match="not in allowed prefixes"):
            resolve_context(
                task_id="TEST-001",
                context_hints=["/etc/passwd"],
                repo_root=repo_with_docs,
            )
    
    def test_rejects_path_traversal(self, repo_with_docs):
        """Path traversal rejected with ContextResolutionError."""
        with pytest.raises(ContextResolutionError, match="path traversal"):
            resolve_context(
                task_id="TEST-001",
                context_hints=["docs/../../../etc/passwd"],
                repo_root=repo_with_docs,
            )
    
    def test_rejects_out_of_envelope(self, repo_with_docs):
        """Paths outside allowlist rejected."""
        with pytest.raises(ContextResolutionError, match="not in allowed prefixes"):
            resolve_context(
                task_id="TEST-001",
                context_hints=["secrets/api_keys.txt"],
                repo_root=repo_with_docs,
            )
    
    def test_allows_known_root_files(self, repo_with_docs):
        """Known root files like GEMINI.md are allowed."""
        result = resolve_context(
            task_id="TEST-001",
            context_hints=["GEMINI.md"],
            repo_root=repo_with_docs,
        )
        assert "GEMINI.md" in result.resolved_paths


class TestFailClosed:
    """Tests for fail-closed behavior."""
    
    def test_fails_on_unresolved_by_default(self, repo_with_docs):
        """Unresolved hints raise error by default."""
        with pytest.raises(ContextResolutionError, match="Unresolved hints"):
            resolve_context(
                task_id="TEST-001",
                context_hints=["docs/nonexistent.md"],
                repo_root=repo_with_docs,
            )
    
    def test_allows_unresolved_when_disabled(self, repo_with_docs):
        """Unresolved tracked but not raised when disabled."""
        result = resolve_context(
            task_id="TEST-001",
            context_hints=["docs/nonexistent.md"],
            repo_root=repo_with_docs,
            fail_on_unresolved=False,
        )
        assert "docs/nonexistent.md" in result.unresolved_hints
        assert len(result.resolved_paths) == 0
    
    def test_envelope_error_always_fails(self, repo_with_docs):
        """Envelope violations always fail regardless of flag."""
        # Use path that starts with allowed prefix but contains traversal
        with pytest.raises(ContextResolutionError, match="path traversal"):
            resolve_context(
                task_id="TEST-001",
                context_hints=["docs/../../../outside.md"],
                repo_root=repo_with_docs,
                fail_on_unresolved=False,  # Still fails on envelope error
            )


class TestResolvedContext:
    """Tests for ResolvedContext dataclass."""
    
    def test_immutable(self, repo_with_docs):
        """ResolvedContext is frozen."""
        result = resolve_context(
            task_id="TEST-001",
            context_hints=[],
            repo_root=repo_with_docs,
        )
        with pytest.raises(AttributeError):
            result.task_id = "CHANGED"
    
    def test_all_fields_populated(self, repo_with_docs):
        """All fields present in result."""
        result = resolve_context(
            task_id="TEST-001",
            context_hints=["docs/11_admin/LIFEOS_STATE.md"],
            repo_root=repo_with_docs,
        )
        assert result.task_id == "TEST-001"
        assert isinstance(result.resolved_paths, tuple)
        assert isinstance(result.baseline_paths, tuple)
        assert isinstance(result.unresolved_hints, tuple)
