"""
Bypass monitor wiring integration tests for LoopSpine (Trusted Builder P1).

Verifies that after each run, bypass utilization is checked, warnings are
emitted at warn/alert level, and the terminal packet carries bypass_utilization.
"""
from __future__ import annotations

import logging
import yaml
import pytest
from unittest.mock import patch

from runtime.orchestration.loop.spine import LoopSpine, SpineState
from runtime.orchestration.loop.bypass_monitor import BypassStatus


@pytest.fixture
def repo_root(tmp_path):
    """Minimal repo structure for spine integration tests."""
    root = tmp_path / "repo"
    root.mkdir()
    (root / "artifacts" / "terminal").mkdir(parents=True)
    (root / "artifacts" / "checkpoints").mkdir(parents=True)
    (root / "artifacts" / "loop_state").mkdir(parents=True)
    (root / "artifacts" / "steps").mkdir(parents=True)
    return root


def test_bypass_warn_logged_and_in_terminal_packet(repo_root, caplog):
    """
    When bypass utilization is at warn level:
    - spine logs a BYPASS_WARN warning
    - terminal packet YAML carries bypass_utilization with correct values
    """
    spine = LoopSpine(repo_root=repo_root)
    warn_status = BypassStatus(level="warn", bypass_count=3, total_count=5, rate=0.6)

    with caplog.at_level(logging.WARNING, logger="runtime.orchestration.loop.spine"):
        with patch("runtime.orchestration.loop.spine.verify_repo_clean"), \
             patch.object(LoopSpine, "_get_current_policy_hash", return_value="test_hash"), \
             patch.object(spine, "_run_chain_steps", return_value={
                 "outcome": "PASS",
                 "steps_executed": ["hydrate", "policy"],
                 "commit_hash": "abc123",
             }), \
             patch(
                 "runtime.orchestration.loop.spine.check_bypass_utilization",
                 return_value=warn_status,
             ):
            result = spine.run(task_spec={"task": "test"})

    assert result["outcome"] == "PASS"

    # Assert BYPASS_WARN was logged
    warn_messages = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    assert any("BYPASS_WARN" in msg for msg in warn_messages), (
        f"Expected BYPASS_WARN in warning logs, got: {warn_messages}"
    )

    # Assert terminal packet carries bypass_utilization
    terminal_packets = list((repo_root / "artifacts" / "terminal").glob("TP_*.yaml"))
    assert len(terminal_packets) == 1
    packet_data = yaml.safe_load(terminal_packets[0].read_text())
    assert "bypass_utilization" in packet_data, (
        f"bypass_utilization missing from terminal packet keys: {list(packet_data.keys())}"
    )
    bu = packet_data["bypass_utilization"]
    assert bu["level"] == "warn"
    assert bu["bypass_count"] == 3
    assert bu["total_count"] == 5
