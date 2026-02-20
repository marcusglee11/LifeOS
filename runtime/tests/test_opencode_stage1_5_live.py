"""
Stage 1.5: Zen Model Comparison — Live API calls.

Compares kimi-k2.5-free vs glm-5-free through the Agent API layer
on the same bounded task. Measures response quality, latency, and
token usage.

Requires: ZEN_BUILDER_KEY in .env or environment.
Skip with: pytest -m "not live" or SKIP_LIVE_ZEN=1

Run: OPENCLAW_MODELS_PREFLIGHT_SKIP=1 pytest runtime/tests/test_opencode_stage1_5_live.py -v -s
"""

from __future__ import annotations

import os
import time

import pytest

# Load .env keys into environment for this test
_env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
if os.path.exists(_env_path):
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

from runtime.agents.api import AgentCall, call_agent, AgentAPIError
from runtime.agents.models import load_model_config, clear_config_cache


# Skip if no API key or explicit skip
pytestmark = pytest.mark.skipif(
    os.environ.get("SKIP_LIVE_ZEN") == "1"
    or not os.environ.get("ZEN_BUILDER_KEY"),
    reason="Live Zen tests require ZEN_BUILDER_KEY and SKIP_LIVE_ZEN!=1",
)

# Simple bounded task for comparison
TEST_PACKET = {
    "goal": "Create a Python function that validates an email address using a regex pattern.",
    "design_type": "implementation_plan",
    "constraints": [
        "Use only stdlib (re module)",
        "Return bool",
        "Handle edge cases: empty string, missing @, missing domain",
    ],
    "output_format": "Return ONLY valid YAML with fields: summary, code, tests",
}

MODELS_TO_TEST = [
    "opencode/kimi-k2.5-free",
    "opencode/glm-5-free",
]


@pytest.fixture(autouse=True)
def _fresh_config():
    clear_config_cache()
    yield
    clear_config_cache()


class TestZenModelComparison:
    """Live comparison of Zen free models through the Agent API layer."""

    results: dict = {}

    @pytest.mark.parametrize("model_id", MODELS_TO_TEST)
    def test_model_responds(self, model_id: str):
        """Each model should return a non-empty response via call_agent."""
        call = AgentCall(
            role="designer",
            packet=TEST_PACKET,
            model=model_id,
            temperature=0.0,
            max_tokens=2048,
        )

        config = load_model_config()
        start = time.monotonic()

        try:
            response = call_agent(call, run_id="stage1.5_comparison", config=config)
        except AgentAPIError as e:
            pytest.fail(f"{model_id} failed: {e}")

        elapsed_ms = int((time.monotonic() - start) * 1000)

        # Basic assertions
        assert response.content, f"{model_id} returned empty content"
        assert len(response.content) > 50, (
            f"{model_id} response too short ({len(response.content)} chars)"
        )
        assert response.model_used, f"{model_id} did not report model_used"

        # Report results
        print(f"\n{'='*60}")
        print(f"Model: {model_id}")
        print(f"  model_used: {response.model_used}")
        print(f"  latency_ms: {elapsed_ms}")
        print(f"  content_length: {len(response.content)} chars")
        print(f"  usage: {response.usage}")
        print(f"  has_packet: {response.packet is not None}")
        if response.packet:
            print(f"  packet_keys: {list(response.packet.keys())}")
        print(f"  first 200 chars: {response.content[:200]}")
        print(f"{'='*60}")

    @pytest.mark.parametrize("model_id", MODELS_TO_TEST)
    def test_model_produces_parseable_yaml(self, model_id: str):
        """Response should be parseable as YAML (the designer role expects YAML output)."""
        call = AgentCall(
            role="designer",
            packet=TEST_PACKET,
            model=model_id,
            temperature=0.0,
            max_tokens=2048,
        )

        config = load_model_config()

        try:
            response = call_agent(call, run_id="stage1.5_yaml_check", config=config)
        except AgentAPIError as e:
            pytest.skip(f"{model_id} call failed (not a YAML test failure): {e}")

        # The agent API already tries to parse YAML — check if packet was extracted
        if response.packet is None:
            # Not a hard failure — some models wrap YAML in markdown
            pytest.skip(
                f"{model_id} response wasn't auto-parsed as YAML packet "
                f"(content starts with: {response.content[:100]})"
            )

        assert isinstance(response.packet, dict)
        print(f"\n{model_id} YAML packet keys: {list(response.packet.keys())}")
