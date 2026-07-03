"""Tests for tools/validate_doc_drift_gate.py."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

TOOL_PATH = Path(__file__).parent.parent / "tools" / "validate_doc_drift_gate.py"
REGISTRY_SRC = Path(__file__).parent.parent / "config" / "docs" / "authority_registry.yaml"
SCHEMA_SRC = (
    Path(__file__).parent.parent / "config" / "schemas" / "doc_authority_registry_v1.json"
)


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def gate_repo(tmp_path: Path) -> Path:
    """Create a temp git repo with authority registry committed.

    Returns the repo root path. Base state is at HEAD~1, test state at HEAD.
    """
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path, check=True, capture_output=True,
    )

    # Copy registry + schema
    (tmp_path / "config" / "docs").mkdir(parents=True)
    (tmp_path / "config" / "schemas").mkdir(parents=True)
    shutil.copy(REGISTRY_SRC, tmp_path / "config" / "docs" / "authority_registry.yaml")
    shutil.copy(SCHEMA_SRC, tmp_path / "config" / "schemas" / "doc_authority_registry_v1.json")

    # Create doc dirs referenced by registry
    doc_dirs = [
        "docs/00_foundations",
        "docs/01_governance",
        "docs/02_protocols",
        "docs/03_runtime",
        "docs/04_project_builder",
        "docs/05_agents",
        "docs/06_user_surface",
        "docs/08_manuals",
        "docs/09_prompts",
        "docs/10_meta/reconciliation_packets",
        "docs/11_admin",
        "docs/12_productisation",
    ]
    for d in doc_dirs:
        (tmp_path / d).mkdir(parents=True)

    # Create sample docs (need to match registry globs)
    (tmp_path / "docs" / "00_foundations" / "architecture.md").write_text("# Architecture")
    (tmp_path / "docs" / "INDEX.md").write_text("# Index")
    (tmp_path / "docs" / "LifeOS_Strategic_Corpus.md").write_text("# Strategic Corpus")

    # Initial commit
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmp_path, check=True, capture_output=True,
    )

    return tmp_path


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def run_gate(
    repo_root: Path, base_ref: str = "HEAD~1", head_ref: str = "HEAD",
) -> tuple[int, dict]:
    """Run validator and return (exit_code, parsed_json)."""
    result = subprocess.run(
        [
            sys.executable, str(TOOL_PATH),
            "--repo-root", str(repo_root),
            "--base-ref", base_ref,
            "--head-ref", head_ref,
        ],
        capture_output=True, text=True,
    )
    try:
        data = json.loads(result.stdout)
    except (json.JSONDecodeError, ValueError):
        pytest.fail(f"Invalid JSON output:\nstdout: {result.stdout}\nstderr: {result.stderr}")
    return result.returncode, data


def _add_commit(repo_root: Path, msg: str) -> None:
    subprocess.run(["git", "add", "."], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", msg],
        cwd=repo_root, check=True, capture_output=True,
    )


def _write_file(repo_root: Path, rel_path: str, content: str) -> None:
    path = repo_root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDriftGate:
    """Doc Drift Gate test suite."""

    def test_canonical_change_with_valid_packet(self, gate_repo: Path) -> None:
        """PASS: Change canonical doc + valid reconciliation packet covering it.

        Also update derived surface to satisfy freshness check.
        """
        _write_file(gate_repo, "docs/00_foundations/architecture.md",
                    "# Architecture v2\n")
        _write_file(gate_repo, "docs/10_meta/reconciliation_packets/p1.md",
                    "---\n"
                    "changed_canonical_paths:\n"
                    "  - docs/00_foundations/architecture.md\n"
                    "affected_derived_surfaces:\n"
                    "  - docs/INDEX.md\n"
                    "  - docs/LifeOS_Strategic_Corpus.md\n"
                    "regeneration_required: true\n"
                    "authority_class_changes: []\n"
                    "post_merge_verification_commands:\n"
                    "  - python3 docs/scripts/generate_strategic_context.py\n"
                    "---\n")
        _write_file(gate_repo, "docs/INDEX.md", "# Index v2\n")
        _write_file(gate_repo, "docs/LifeOS_Strategic_Corpus.md", "# Strategic Corpus v2\n")

        _add_commit(gate_repo, "feat: update architecture docs")

        rc, data = run_gate(gate_repo)
        assert rc == 0, f"Expected pass, got:\n{json.dumps(data, indent=2)}"
        assert data["passed"] is True

    def test_canonical_change_without_packet(self, gate_repo: Path) -> None:
        """FAIL: Change canonical doc without a reconciliation packet."""
        _write_file(gate_repo, "docs/00_foundations/architecture.md",
                    "# Architecture v2\n")
        # Also update derived surface — still fails because no packet covers it
        _write_file(gate_repo, "docs/INDEX.md", "# Index v2\n")
        _write_file(gate_repo, "docs/LifeOS_Strategic_Corpus.md", "# Strategic Corpus v2\n")

        _add_commit(gate_repo, "feat: update architecture docs")

        rc, data = run_gate(gate_repo)
        assert rc == 1, f"Expected fail, got:\n{json.dumps(data, indent=2)}"
        assert data["passed"] is False
        assert not data["checks"]["reconciliation"]["passed"]

    def test_canonical_change_with_typo_exemption(self, gate_repo: Path) -> None:
        """PASS: Change canonical doc + typo exemption packet."""
        _write_file(gate_repo, "docs/00_foundations/architecture.md",
                    "# Architecture v2\n")
        _write_file(gate_repo, "docs/10_meta/reconciliation_packets/ex1.md",
                    "---\n"
                    "reconciliation_exemption:\n"
                    "  reason: typo\n"
                    "  affected_derived_surfaces: none\n"
                    "  semantic_change: false\n"
                    "---\n")

        _add_commit(gate_repo, "fix: typo in architecture docs")

        rc, data = run_gate(gate_repo)
        assert rc == 0, f"Expected pass, got:\n{json.dumps(data, indent=2)}"
        assert data["passed"] is True

    def test_canonical_change_with_other_exemption(self, gate_repo: Path) -> None:
        """FAIL: Exemption with reason 'other' is not allowed."""
        _write_file(gate_repo, "docs/00_foundations/architecture.md",
                    "# Architecture v2\n")
        _write_file(gate_repo, "docs/10_meta/reconciliation_packets/ex2.md",
                    "---\n"
                    "reconciliation_exemption:\n"
                    "  reason: other\n"
                    "  affected_derived_surfaces: none\n"
                    "  semantic_change: false\n"
                    "---\n")

        _add_commit(gate_repo, "fix: update architecture docs")

        rc, data = run_gate(gate_repo)
        assert rc == 1, f"Expected fail, got:\n{json.dumps(data, indent=2)}"
        assert data["passed"] is False
        assert not data["checks"]["reconciliation"]["passed"]

    def test_authority_transition_with_approval(self, gate_repo: Path) -> None:
        """PASS: Change registry group authority with valid transition record."""
        # Read current registry
        reg_path = gate_repo / "config" / "docs" / "authority_registry.yaml"
        registry = yaml.safe_load(reg_path.read_text())

        # Change discarded-archives from discarded to proposal-only
        for group in registry["doc_groups"]:
            if group["id"] == "discarded-archives":
                group["authority"] = "proposal-only"

        # Add transition record
        transitions = registry.get("authority_transitions", [])
        transitions.append({
            "changed_paths": ["discarded-archives"],
            "from": "discarded",
            "to": "proposal-only",
            "approval_evidence": {
                "type": "human",
                "url": "https://github.com/owner/repo/issues/42",
                "verdict": "approved",
            },
        })
        registry["authority_transitions"] = transitions

        reg_path.write_text(yaml.dump(registry))

        _add_commit(gate_repo, "feat: change authority of discarded-archives")

        rc, data = run_gate(gate_repo)
        assert rc == 0, f"Expected pass, got:\n{json.dumps(data, indent=2)}"
        assert data["passed"] is True

    def test_authority_transition_without_approval(self, gate_repo: Path) -> None:
        """FAIL: Change registry group authority without transition record."""
        reg_path = gate_repo / "config" / "docs" / "authority_registry.yaml"
        registry = yaml.safe_load(reg_path.read_text())

        # Change discarded-archives from discarded to canonical
        for group in registry["doc_groups"]:
            if group["id"] == "discarded-archives":
                group["authority"] = "canonical"

        reg_path.write_text(yaml.dump(registry))

        _add_commit(gate_repo, "feat: change authority without transition")

        rc, data = run_gate(gate_repo)
        assert rc == 1, f"Expected fail, got:\n{json.dumps(data, indent=2)}"
        assert data["passed"] is False
        assert not data["checks"]["authority_transitions"]["passed"]

    def test_derived_surface_stale(self, gate_repo: Path) -> None:
        """FAIL: Change canonical doc, derived surface not updated, no packet."""
        _write_file(gate_repo, "docs/00_foundations/architecture.md",
                    "# Architecture v2\n")

        _add_commit(gate_repo, "feat: update architecture docs")

        rc, data = run_gate(gate_repo)
        assert rc == 1, f"Expected fail, got:\n{json.dumps(data, indent=2)}"
        assert data["passed"] is False
        # Both reconciliation and derived freshness should fail
        assert not data["checks"]["reconciliation"]["passed"]

    def test_derived_surface_fresh(self, gate_repo: Path) -> None:
        """PASS: Change canonical doc, derived surface also updated, valid packet."""
        _write_file(gate_repo, "docs/00_foundations/architecture.md",
                    "# Architecture v2\n")
        _write_file(gate_repo, "docs/INDEX.md", "# Index v2\n")
        _write_file(gate_repo, "docs/LifeOS_Strategic_Corpus.md", "# Strategic Corpus v2\n")
        _write_file(gate_repo, "docs/10_meta/reconciliation_packets/p1.md",
                    "---\n"
                    "changed_canonical_paths:\n"
                    "  - docs/00_foundations/architecture.md\n"
                    "affected_derived_surfaces:\n"
                    "  - docs/INDEX.md\n"
                    "  - docs/LifeOS_Strategic_Corpus.md\n"
                    "regeneration_required: true\n"
                    "authority_class_changes: []\n"
                    "post_merge_verification_commands:\n"
                    "  - python3 docs/scripts/generate_strategic_context.py\n"
                    "---\n")

        _add_commit(gate_repo, "feat: update architecture and index")

        rc, data = run_gate(gate_repo)
        assert rc == 0, f"Expected pass, got:\n{json.dumps(data, indent=2)}"
        assert data["passed"] is True

    def test_emergency_repair_valid(self, gate_repo: Path) -> None:
        """PASS: Edit derived file with valid emergency-manual-repair frontmatter."""
        _write_file(gate_repo, "docs/LifeOS_Strategic_Corpus.md",
                    "---\n"
                    "derived_edit_mode: emergency-manual-repair\n"
                    "reason: critical error in published content\n"
                    "follow_up_required: true\n"
                    "follow_up_issue: https://github.com/owner/repo/issues/42\n"
                    "approval_evidence: https://github.com/owner/repo/issues/42#issuecomment-1\n"
                    "---\n"
                    "# Strategic Corpus (fixed)\n")

        _add_commit(gate_repo, "fix: emergency repair strategic corpus")

        rc, data = run_gate(gate_repo)
        assert rc == 0, f"Expected pass, got:\n{json.dumps(data, indent=2)}"
        assert data["passed"] is True

    def test_emergency_repair_pending(self, gate_repo: Path) -> None:
        """FAIL: Edit derived file with follow_up_issue: pending."""
        _write_file(gate_repo, "docs/LifeOS_Strategic_Corpus.md",
                    "---\n"
                    "derived_edit_mode: emergency-manual-repair\n"
                    "reason: quick fix\n"
                    "follow_up_required: true\n"
                    "follow_up_issue: pending\n"
                    "approval_evidence: https://github.com/owner/repo/issues/42\n"
                    "---\n"
                    "# Strategic Corpus (fixed)\n")

        _add_commit(gate_repo, "fix: emergency repair strategic corpus")

        rc, data = run_gate(gate_repo)
        assert rc == 1, f"Expected fail, got:\n{json.dumps(data, indent=2)}"
        assert data["passed"] is False
        assert not data["checks"]["emergency_repair"]["passed"]

    def test_non_doc_changes(self, gate_repo: Path) -> None:
        """PASS: Only non-doc files changed, gate should trivially pass."""
        _write_file(gate_repo, "runtime/test.py", "# test\n")

        _add_commit(gate_repo, "chore: add test file")

        rc, data = run_gate(gate_repo)
        assert rc == 0, f"Expected pass, got:\n{json.dumps(data, indent=2)}"
        assert data["passed"] is True

    def test_stale_derived_with_not_affected_reason(self, gate_repo: Path) -> None:
        """PASS: Change canonical doc, derived not updated, packet says not affected."""
        _write_file(gate_repo, "docs/00_foundations/architecture.md",
                    "# Architecture v2\n")
        _write_file(gate_repo, "docs/10_meta/reconciliation_packets/p1.md",
                    "---\n"
                    "changed_canonical_paths:\n"
                    "  - docs/00_foundations/architecture.md\n"
                    "affected_derived_surfaces:\n"
                    "  - docs/INDEX.md\n"
                    "regeneration_required: false\n"
                    "not_affected_reason: Trivial whitespace change only\n"
                    "authority_class_changes: []\n"
                    "post_merge_verification_commands: []\n"
                    "---\n")

        _add_commit(gate_repo, "fix: whitespace in architecture docs")

        rc, data = run_gate(gate_repo)
        assert rc == 0, f"Expected pass, got:\n{json.dumps(data, indent=2)}"
        assert data["passed"] is True
