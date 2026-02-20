"""
Stage 3: Build→Steward Pipeline Integration Tests.

Proves that the infrastructure fix (build mission writes files to disk)
enables a complete build→review→steward chain.

Test tiers:
  1. Mocked (no API calls) — always run
  2. Free-model live          — RUN_LIVE_STAGE3_FREE=1
  3. Paid-model live          — RUN_LIVE_STAGE3_PAID=1
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from runtime.agents.api import AgentResponse
from runtime.orchestration.missions.base import MissionContext
from runtime.orchestration.missions.build import BuildMission
from runtime.orchestration.missions.review import ReviewMission
from runtime.orchestration.missions.steward import StewardMission


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_agent_response(role: str, content: str, packet=None) -> AgentResponse:
    return AgentResponse(
        call_id=f"test-{role}",
        call_id_audit=f"audit-{role}",
        role=role,
        model_used="mock-model",
        model_version="0",
        content=content,
        packet=packet,
        usage={},
        latency_ms=10,
        timestamp="2026-02-20T00:00:00Z",
    )


def _git(args, cwd):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


def _head(cwd):
    return _git(["git", "rev-parse", "HEAD"], cwd).stdout.strip()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def git_repo(tmp_path):
    """Real git repo with a Python file to modify."""
    _git(["git", "init", "."], cwd=tmp_path)
    _git(["git", "config", "user.email", "test@lifeos.local"], cwd=tmp_path)
    _git(["git", "config", "user.name", "LifeOS Test"], cwd=tmp_path)

    target_dir = tmp_path / "runtime" / "agents"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "models.py"
    target.write_text(
        "def clear_config_cache():\n"
        "    _cache.clear()\n"
    )
    _git(["git", "add", "."], cwd=tmp_path)
    _git(["git", "commit", "--no-verify", "-m", "Initial: add target file"], cwd=tmp_path)
    return tmp_path


@pytest.fixture
def ctx(git_repo):
    return MissionContext(
        repo_root=git_repo,
        baseline_commit=_head(git_repo),
        run_id="stage3-test",
        operation_executor=None,
        journal=None,
    )


# ---------------------------------------------------------------------------
# Tier 1: Mocked — no API calls
# ---------------------------------------------------------------------------

class TestBuildWritesFiles:
    """Verify _apply_build_packet writes files when call_agent returns a packet."""

    def test_create_file_from_packet(self, ctx, git_repo):
        """Build mission writes a new file from LLM packet."""
        build_packet = {
            "files": [
                {
                    "path": "runtime/agents/new_util.py",
                    "action": "create",
                    "content": "def helper():\n    return True\n",
                }
            ]
        }
        mock_response = _make_agent_response("builder", "Done", build_packet)
        mission = BuildMission()

        with patch("runtime.agents.api.call_agent", return_value=mock_response):
            result = mission.run(ctx, {
                "build_packet": {"goal": "Add helper utility"},
                "approval": {"verdict": "approved"},
            })

        assert result.success is True
        new_file = git_repo / "runtime" / "agents" / "new_util.py"
        assert new_file.exists()
        assert "def helper" in new_file.read_text()
        artifacts = result.outputs["review_packet"]["payload"]["artifacts_produced"]
        assert "runtime/agents/new_util.py" in artifacts

    def test_modify_file_from_packet(self, ctx, git_repo):
        """Build mission overwrites existing file with new content from packet."""
        modified_content = (
            "def clear_config_cache():\n"
            '    """Clear the config cache."""\n'
            "    _cache.clear()\n"
        )
        build_packet = {
            "files": [
                {
                    "path": "runtime/agents/models.py",
                    "action": "modify",
                    "content": modified_content,
                }
            ]
        }
        mock_response = _make_agent_response("builder", "Done", build_packet)
        mission = BuildMission()

        with patch("runtime.agents.api.call_agent", return_value=mock_response):
            result = mission.run(ctx, {
                "build_packet": {"goal": "Add docstring to clear_config_cache"},
                "approval": {"verdict": "approved"},
            })

        assert result.success is True
        content = (git_repo / "runtime" / "agents" / "models.py").read_text()
        assert "Clear the config cache" in content
        artifacts = result.outputs["review_packet"]["payload"]["artifacts_produced"]
        assert "runtime/agents/models.py" in artifacts


class TestFullChainMocked:
    """End-to-end: build writes file → review approves → steward commits."""

    def test_build_review_steward_commit(self, ctx, git_repo):
        """Full chain with mocked LLM calls produces a real git commit."""
        head_before = _head(git_repo)

        # --- Build ---
        modified_content = (
            "def clear_config_cache():\n"
            '    """Clear the config cache."""\n'
            "    _cache.clear()\n"
        )
        builder_packet = {
            "files": [
                {
                    "path": "runtime/agents/models.py",
                    "action": "modify",
                    "content": modified_content,
                }
            ]
        }
        builder_response = _make_agent_response("builder", "Done", builder_packet)

        build_mission = BuildMission()
        with patch("runtime.agents.api.call_agent", return_value=builder_response):
            build_result = build_mission.run(ctx, {
                "build_packet": {"goal": "Add docstring to clear_config_cache"},
                "approval": {"verdict": "approved"},
            })

        assert build_result.success is True
        review_packet = build_result.outputs["review_packet"]
        assert review_packet["payload"]["artifacts_produced"], "Build must detect changed files"

        # --- Review ---
        reviewer_content = (
            "verdict: approved\n"
            "rationale: Docstring added correctly.\n"
        )
        reviewer_packet = {"verdict": "approved", "rationale": "Docstring added correctly."}
        reviewer_response = _make_agent_response("reviewer_architect", reviewer_content, reviewer_packet)

        review_mission = ReviewMission()
        with patch("runtime.agents.api.call_agent", return_value=reviewer_response):
            review_result = review_mission.run(ctx, {
                "subject_packet": review_packet,
                "review_type": "build_review",
            })

        assert review_result.success is True
        verdict = review_result.outputs["verdict"]
        assert verdict == "approved", f"Reviewer returned non-approved verdict: {verdict}"

        # --- Steward ---
        steward_mission = StewardMission()
        steward_result = steward_mission.run(ctx, {
            "review_packet": review_packet,
            "approval": {"verdict": verdict},
        })

        assert steward_result.success is True, f"Steward failed: {steward_result.error}"
        commit_hash = steward_result.outputs.get("commit_hash")
        assert commit_hash is not None, "Steward must produce a commit_hash"

        head_after = _head(git_repo)
        assert head_after != head_before, "HEAD must advance after steward commit"

        # Verify docstring is in the committed file
        file_at_head = subprocess.run(
            ["git", "show", f"HEAD:runtime/agents/models.py"],
            cwd=git_repo, capture_output=True, text=True, check=True
        ).stdout
        assert "Clear the config cache" in file_at_head


# ---------------------------------------------------------------------------
# Tier 2: Free-model live spine run (skipped unless RUN_LIVE_STAGE3_FREE=1)
# ---------------------------------------------------------------------------

_LIVE_TASK = "Add docstrings to sign_payload and verify_signature in runtime/sign.py"


@pytest.mark.skipif(
    os.environ.get("RUN_LIVE_STAGE3_FREE") != "1",
    reason="Set RUN_LIVE_STAGE3_FREE=1 to run live test with free models",
)
def test_live_spine_free_models():
    """
    Live: full spine run with current free-model config.
    Measures: success/failure, latency, commit evidence.
    This test records results but does NOT assert PASS — free models may fail.
    """
    os.environ.setdefault("OPENCLAW_MODELS_PREFLIGHT_SKIP", "1")

    from runtime.orchestration.loop.spine import LoopSpine

    repo_root = Path(__file__).parent.parent.parent

    # Restore files dirtied by previous failed runs so pre-flight passes.
    subprocess.run(
        ["git", "checkout", "HEAD", "--",
         "artifacts/loop_state/attempt_ledger.jsonl",
         "runtime/sign.py"],
        cwd=repo_root, capture_output=True,
    )

    task_spec = {"task": _LIVE_TASK}
    spine = LoopSpine(repo_root=repo_root)

    t0 = time.monotonic()
    result = spine.run(task_spec=task_spec)
    elapsed = time.monotonic() - t0

    model_label = "free (kimi-k2.5-free / glm-5-free)"
    _log_comparison_result(model_label, result, elapsed, repo_root)

    print(f"\n[FREE MODEL] outcome={result['outcome']} elapsed={elapsed:.1f}s")
    # Intentionally not asserting PASS — record baseline, comparison will show diff


# ---------------------------------------------------------------------------
# Tier 3: Paid-model live spine run (skipped unless RUN_LIVE_STAGE3_PAID=1)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    os.environ.get("RUN_LIVE_STAGE3_PAID") != "1",
    reason="Set RUN_LIVE_STAGE3_PAID=1 to run live test with paid models (costs $)",
)
def test_live_spine_paid_models():
    """
    Live: full spine run with paid model config (claude-sonnet-4-5 via OpenRouter).
    Swap models.yaml temporarily for designer+builder+steward, then restore.
    Measures: success/failure, latency, commit evidence.
    """
    os.environ.setdefault("OPENCLAW_MODELS_PREFLIGHT_SKIP", "1")

    paid_model = os.environ.get(
        "STAGE3_PAID_MODEL",
        "openrouter/anthropic/claude-sonnet-4-5",
    )

    from runtime.orchestration.loop.spine import LoopSpine

    repo_root = Path(__file__).parent.parent.parent

    # Restore any files dirtied by previous failed runs (ledger, task target file).
    # The spine pre-flight check requires a completely clean repo.
    subprocess.run(
        ["git", "checkout", "HEAD", "--",
         "artifacts/loop_state/attempt_ledger.jsonl",
         "runtime/sign.py"],
        cwd=repo_root, capture_output=True,
    )

    # Use LIFEOS_MODEL_OVERRIDE env var — avoids writing models.yaml which would dirty the repo
    os.environ["LIFEOS_MODEL_OVERRIDE"] = paid_model
    os.environ.setdefault("OPENROUTER_API_KEY", os.environ.get("OPENROUTER_API_KEY", ""))

    try:
        task_spec = {"task": _LIVE_TASK}
        spine = LoopSpine(repo_root=repo_root)

        t0 = time.monotonic()
        result = spine.run(task_spec=task_spec)
        elapsed = time.monotonic() - t0

        model_label = f"paid ({paid_model})"
        _log_comparison_result(model_label, result, elapsed, repo_root)

        print(f"\n[PAID MODEL] outcome={result['outcome']} elapsed={elapsed:.1f}s commit={result.get('commit_hash')}")
        assert result["outcome"] == "PASS", (
            f"Paid-model spine failed: {result}\n"
            f"Check artifacts/terminal/ for TP_*.yaml"
        )
    finally:
        os.environ.pop("LIFEOS_MODEL_OVERRIDE", None)


# ---------------------------------------------------------------------------
# Comparison logger
# ---------------------------------------------------------------------------

def _log_comparison_result(
    model_label: str,
    result: dict,
    elapsed_seconds: float,
    repo_root: Path,
) -> None:
    """Append a comparison row to artifacts/comparison_results.jsonl."""
    row = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "model": model_label,
        "outcome": result.get("outcome"),
        "commit_hash": result.get("commit_hash"),
        "elapsed_seconds": round(elapsed_seconds, 1),
        "run_id": result.get("run_id"),
    }
    log_path = repo_root / "artifacts" / "comparison_results.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a") as f:
        f.write(json.dumps(row) + "\n")
    print(f"\n[COMPARISON] {model_label}: {row}")
