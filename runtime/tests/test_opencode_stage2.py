"""
Stage 2: Design Mission Fallback Extraction Tests.

Verifies that DesignMission._extract_fallback_packet() correctly extracts
BUILD_PACKETs from raw LLM prose when response.packet is None, and that
the fallback is integrated into the run() happy path.

No live API calls — all tests use mocked call_agent.
One live test is skipped unless RUN_LIVE_STAGE2=1 is set.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from runtime.agents.api import AgentResponse
from runtime.orchestration.missions.design import DesignMission
from runtime.orchestration.missions.base import MissionContext


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def ctx() -> MissionContext:
    return MissionContext(
        run_id="test-stage2-run",
        repo_root=Path("."),
        baseline_commit="0000000000000000000000000000000000000000",
    )


@pytest.fixture
def mission() -> DesignMission:
    return DesignMission()


def _make_response(content: str, packet=None) -> AgentResponse:
    return AgentResponse(
        call_id="test-call-id",
        call_id_audit="test-audit-id",
        role="designer",
        model_used="test-model",
        model_version="0",
        content=content,
        packet=packet,
        usage={},
        latency_ms=10,
        timestamp="2026-02-19T00:00:00Z",
    )


# ---------------------------------------------------------------------------
# Unit tests for _extract_fallback_packet
# ---------------------------------------------------------------------------

class TestExtractFallbackPacket:
    """Unit tests for the three extraction strategies."""

    def test_strategy1_yaml_codeblock(self, mission):
        """Strategy 1: YAML wrapped in a code block."""
        content = """
Here is the design packet:

```yaml
goal: Add a docstring to clear_config_cache
scope: runtime/agents/models.py
```
"""
        result = mission._extract_fallback_packet(content, "Add docstring")
        assert result is not None
        assert result["goal"] == "Add a docstring to clear_config_cache"
        assert result["_source"] == "yaml_codeblock"

    def test_strategy2_bare_goal_field(self, mission):
        """Strategy 2: Bare goal: field in prose."""
        content = "goal: Add a docstring to clear_config_cache\nscope: models.py"
        result = mission._extract_fallback_packet(content, "Add docstring")
        assert result is not None
        assert result.get("goal") == "Add a docstring to clear_config_cache"
        assert result["_source"] in ("bare_yaml", "bare_goal_field")

    def test_strategy3_tool_output_passthrough(self, mission):
        """Strategy 3: Model did the work directly."""
        content = "I have added a docstring to clear_config_cache in models.py."
        result = mission._extract_fallback_packet(content, "Add docstring")
        assert result is not None
        assert result["goal"] == "Add docstring"
        assert result["_source"] == "tool_output_passthrough"

    def test_empty_content_returns_none(self, mission):
        """Empty or whitespace-only content returns None."""
        assert mission._extract_fallback_packet("", "task") is None
        assert mission._extract_fallback_packet("   \n  ", "task") is None

    def test_unrecognised_content_returns_none(self, mission):
        """Content with no extractable packet returns None."""
        content = "The model is thinking carefully about this request."
        result = mission._extract_fallback_packet(content, "task")
        assert result is None


# ---------------------------------------------------------------------------
# Integration test: fallback wired into run()
# ---------------------------------------------------------------------------

class TestDesignMissionFallbackIntegration:
    """Verify fallback is used inside run() when packet is None."""

    def test_run_uses_fallback_when_packet_none(self, mission, ctx):
        """When call_agent returns packet=None but prose has a goal, use fallback."""
        prose = "```yaml\ngoal: Add a docstring to clear_config_cache\n```"
        mock_response = _make_response(content=prose, packet=None)

        with patch("runtime.agents.api.call_agent", return_value=mock_response):
            result = mission.run(ctx, {"task_spec": "Add docstring"})

        assert result.success is True
        assert result.outputs["build_packet"]["goal"] == "Add a docstring to clear_config_cache"
        assert result.evidence.get("packet_source") == "fallback_extraction"
        assert result.evidence.get("fallback_strategy") == "yaml_codeblock"


# ---------------------------------------------------------------------------
# Live integration test (skipped by default)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    __import__("os").environ.get("RUN_LIVE_STAGE2") != "1",
    reason="Set RUN_LIVE_STAGE2=1 to run live spine call",
)
def test_live_spine_design_step(ctx):
    """Live: run DesignMission against real API and confirm BUILD_PACKET produced."""
    import os
    os.environ.setdefault("OPENCLAW_MODELS_PREFLIGHT_SKIP", "1")

    mission = DesignMission()
    result = mission.run(ctx, {"task_spec": "Add a docstring to clear_config_cache in runtime/agents/models.py"})

    assert result.success is True, f"Live design step failed: {result.error}"
    assert "build_packet" in result.outputs
    assert result.outputs["build_packet"].get("goal")
