"""
Shared pytest fixtures for runtime/tests/receipts/.
"""

from __future__ import annotations

import pytest

from runtime.receipts.plan_core import compute_plan_core_sha256


@pytest.fixture
def sample_plan_core_dict() -> dict:
    """A minimal but valid PlanCore dict with phase_order."""
    return {
        "plan_id": "plan-test-001",
        "schema_version": "1.0",
        "phase_order": ["init", "build", "review"],
        "phases": {
            "init": {"steps": [{"step_id": "s1", "name": "Initialize"}]},
            "build": {"steps": [{"step_id": "s2", "name": "Build"}]},
            "review": {"steps": [{"step_id": "s3", "name": "Review"}]},
        },
        "metadata": {"project": "lifeos-test"},
    }


@pytest.fixture
def sample_workspace_sha() -> str:
    """A sample workspace commit SHA (40-char hex)."""
    return "abc123def456abc123def456abc123def456abc1"


@pytest.fixture
def sample_workspace_tree_oid() -> str:
    """A sample workspace tree OID (40-char hex)."""
    return "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"


@pytest.fixture
def sample_plan_core_sha256(sample_plan_core_dict) -> str:
    """SHA-256 of the sample plan core."""
    return compute_plan_core_sha256(sample_plan_core_dict)


@pytest.fixture
def sample_gate_results() -> list[dict]:
    """A set of gate results covering PASS/FAIL/WARN/BLOCKED."""
    return [
        {"gate_id": "gate-lint", "status": "PASS", "blocking": True},
        {"gate_id": "gate-tests", "status": "PASS", "blocking": True},
        {"gate_id": "gate-coverage", "status": "WARN", "blocking": False},
    ]


@pytest.fixture
def sample_failing_gate_results() -> list[dict]:
    """Gate results that include a blocking failure."""
    return [
        {"gate_id": "gate-lint", "status": "PASS", "blocking": True},
        {"gate_id": "gate-tests", "status": "FAIL", "blocking": True},
        {"gate_id": "gate-coverage", "status": "WARN", "blocking": False},
    ]


@pytest.fixture
def tmp_store(tmp_path):
    """A temporary store directory."""
    store_path = tmp_path / "store"
    store_path.mkdir()
    return store_path


@pytest.fixture
def mock_resolve_tree_oid(monkeypatch, sample_workspace_tree_oid):
    """
    Monkeypatch resolve_tree_oid to avoid real git calls in unit tests.
    Returns the sample_workspace_tree_oid for any SHA.
    """
    import runtime.receipts.plan_core as pc

    def _mock_resolver(sha: str, repo_root=None) -> str:
        return sample_workspace_tree_oid

    monkeypatch.setattr(pc, "resolve_tree_oid", _mock_resolver)
    return _mock_resolver
