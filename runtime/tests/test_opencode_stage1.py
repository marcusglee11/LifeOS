"""
Stage 1: Agent API Layer Tests for OpenCode/Zen integration.

Verifies that config/models.yaml is correctly loaded and resolved
by the runtime agent API layer — model resolution, fallback chains,
envelope violations, role prompt loading, and call logging.

No live API calls — all tests use config parsing and mocked transports.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from runtime.agents.models import (
    load_model_config,
    resolve_model_auto,
    get_model_chain,
    clear_config_cache,
    ModelConfig,
)
from runtime.agents.api import (
    _load_role_prompt,
    EnvelopeViolation,
    AgentCall,
    call_agent,
)
from runtime.agents.agent_logging import (
    HASH_CHAIN_GENESIS,
    AgentCallLogger,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_model_cache():
    """Ensure each test gets a fresh config load."""
    clear_config_cache()
    yield
    clear_config_cache()


@pytest.fixture
def config() -> ModelConfig:
    """Load the real config/models.yaml."""
    return load_model_config()


# ---------------------------------------------------------------------------
# Test 1: Model Resolution — correct Zen model per role
# ---------------------------------------------------------------------------

class TestModelResolution:
    """Verify resolve_model_auto reads config/models.yaml and returns correct model per role."""

    def test_builder_resolves_from_agent_config(self, config: ModelConfig):
        """Builder should resolve to claude-sonnet-4-5 (paid Zen model)."""
        model, reason, chain = resolve_model_auto("builder", config)
        assert model == "claude-sonnet-4-5"
        assert reason == "agent_config"

    def test_steward_resolves_from_agent_config(self, config: ModelConfig):
        """Steward should resolve to claude-sonnet-4-5 (paid Zen model)."""
        model, reason, chain = resolve_model_auto("steward", config)
        assert model == "claude-sonnet-4-5"
        assert reason == "agent_config"

    def test_designer_resolves_from_agent_config(self, config: ModelConfig):
        """Designer should resolve to claude-sonnet-4-5 (paid Zen model)."""
        model, reason, chain = resolve_model_auto("designer", config)
        assert model == "claude-sonnet-4-5"
        assert reason == "agent_config"

    def test_reviewer_architect_resolves_from_agent_config(self, config: ModelConfig):
        """Reviewer architect should resolve to claude-sonnet-4-5 (paid Zen model)."""
        model, reason, chain = resolve_model_auto("reviewer_architect", config)
        assert model == "claude-sonnet-4-5"
        assert reason == "agent_config"

    def test_build_cycle_resolves_from_agent_config(self, config: ModelConfig):
        """Build cycle should resolve to claude-sonnet-4-5 (paid Zen model)."""
        model, reason, chain = resolve_model_auto("build_cycle", config)
        assert model == "claude-sonnet-4-5"
        assert reason == "agent_config"

    def test_unknown_role_falls_back_to_default_chain(self, config: ModelConfig):
        """Unknown role with no agent config should use default_chain primary."""
        model, reason, chain = resolve_model_auto("unknown_role_xyz", config)
        assert model == "claude-sonnet-4-5"
        assert reason == "primary"
        assert chain == config.default_chain

    def test_all_configured_roles_resolve(self, config: ModelConfig):
        """Every role in agents section should resolve without error."""
        for role in config.agents:
            model, reason, chain = resolve_model_auto(role, config)
            assert model, f"Role {role} resolved to empty model"
            assert reason == "agent_config"


# ---------------------------------------------------------------------------
# Test 2: Fallback Chain — glm-5-free present, correct ordering
# ---------------------------------------------------------------------------

class TestFallbackChain:
    """Verify fallback chains have paid primary + free fallbacks."""

    def test_default_chain_includes_glm5(self, config: ModelConfig):
        """Default chain should include glm-5-free as a fallback."""
        assert "opencode/glm-5-free" in config.default_chain

    def test_default_chain_has_paid_primary(self, config: ModelConfig):
        """Default chain primary should be the paid claude-sonnet-4-5 model."""
        assert len(config.default_chain) >= 2
        assert config.default_chain[0] == "claude-sonnet-4-5"
        assert "opencode/glm-5-free" in config.default_chain

    def test_steward_fallback_chain_includes_glm5(self, config: ModelConfig):
        """Steward agent fallback should include glm-5-free."""
        chain = get_model_chain("steward", config)
        assert "opencode/glm-5-free" in chain

    def test_builder_fallback_chain_includes_glm5(self, config: ModelConfig):
        """Builder agent fallback should include glm-5-free."""
        chain = get_model_chain("builder", config)
        assert "opencode/glm-5-free" in chain

    def test_build_cycle_fallback_chain_includes_glm5(self, config: ModelConfig):
        """Build cycle agent fallback should include glm-5-free."""
        chain = get_model_chain("build_cycle", config)
        assert "opencode/glm-5-free" in chain

    def test_all_role_override_chains_include_glm5(self, config: ModelConfig):
        """Every role_overrides chain should include glm-5-free."""
        for role, chain in config.role_overrides.items():
            assert "opencode/glm-5-free" in chain, (
                f"Role override '{role}' missing glm-5-free"
            )

    def test_fallback_chain_length_for_agents(self, config: ModelConfig):
        """Each agent should have primary + fallbacks totaling at least 3 models."""
        for role, agent in config.agents.items():
            chain = get_model_chain(role, config)
            assert len(chain) >= 3, (
                f"Agent '{role}' has only {len(chain)} models in chain"
            )


# ---------------------------------------------------------------------------
# Test 3: Call Logging — deterministic log entry with hash chain
# ---------------------------------------------------------------------------

class TestCallLogging:
    """Verify call_agent produces deterministic log entries with hash chain integrity."""

    def test_logger_produces_chained_entries(self):
        """Logger should produce entries with correct hash chain linkage."""
        logger = AgentCallLogger()

        entry1 = logger.log_call(
            call_id_deterministic="sha256:stage1_test_1",
            call_id_audit="audit-001",
            role="builder",
            model_requested="auto",
            model_used="opencode/minimax-m2.5-free",
            model_version="2026-02-19",
            input_packet_hash="sha256:input1",
            prompt_hash="sha256:prompt1",
            input_tokens=200,
            output_tokens=150,
            latency_ms=2500,
            output_packet_hash="sha256:output1",
            status="success",
        )
        assert entry1.prev_log_hash == HASH_CHAIN_GENESIS

        entry2 = logger.log_call(
            call_id_deterministic="sha256:stage1_test_2",
            call_id_audit="audit-002",
            role="designer",
            model_requested="auto",
            model_used="opencode/kimi-k2.5-free",
            model_version="2026-02-19",
            input_packet_hash="sha256:input2",
            prompt_hash="sha256:prompt2",
            input_tokens=300,
            output_tokens=200,
            latency_ms=3000,
            output_packet_hash="sha256:output2",
            status="success",
        )
        assert entry2.prev_log_hash == entry1.entry_hash

        is_valid, breaks = logger.verify_chain()
        assert is_valid is True
        assert breaks == []

    def test_logger_entry_hash_is_deterministic_with_frozen_time(self):
        """Same inputs + same timestamp should produce identical entry hashes."""
        from datetime import datetime, timezone

        frozen_dt = datetime(2026, 2, 19, 12, 0, 0, tzinfo=timezone.utc)
        logger1 = AgentCallLogger()
        logger2 = AgentCallLogger()

        kwargs = dict(
            call_id_deterministic="sha256:determinism_test",
            call_id_audit="audit-det",
            role="builder",
            model_requested="auto",
            model_used="opencode/minimax-m2.5-free",
            model_version="2026-02-19",
            input_packet_hash="sha256:input_det",
            prompt_hash="sha256:prompt_det",
            input_tokens=100,
            output_tokens=50,
            latency_ms=1000,
            output_packet_hash="sha256:output_det",
            status="success",
        )

        with patch("runtime.agents.logging.datetime") as mock_dt:
            mock_dt.now.return_value = frozen_dt
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            e1 = logger1.log_call(**kwargs)
            e2 = logger2.log_call(**kwargs)

        assert e1.entry_hash == e2.entry_hash


# ---------------------------------------------------------------------------
# Test 4: Envelope Violation — nonexistent role
# ---------------------------------------------------------------------------

class TestEnvelopeViolation:
    """Verify EnvelopeViolation raised for invalid roles."""

    def test_nonexistent_role_raises_envelope_violation(self):
        """call_agent with nonexistent role should raise EnvelopeViolation."""
        call = AgentCall(role="nonexistent_role", packet={"test": True})
        with pytest.raises(EnvelopeViolation, match="Role prompt not found"):
            call_agent(call)

    def test_load_role_prompt_missing_file_raises(self):
        """_load_role_prompt for missing role file should raise EnvelopeViolation."""
        with pytest.raises(EnvelopeViolation, match="Role prompt not found"):
            _load_role_prompt("totally_fake_role")

    def test_steward_role_has_no_prompt_file(self):
        """Steward role has config in models.yaml but no prompt .md file — envelope violation."""
        # steward is configured in models.yaml agents section but has no
        # config/agent_roles/steward.md file, so call_agent should fail
        prompt_path = Path("config/agent_roles/steward.md")
        if prompt_path.exists():
            pytest.skip("steward.md exists — test assumes it doesn't")
        with pytest.raises(EnvelopeViolation, match="Role prompt not found"):
            _load_role_prompt("steward")


# ---------------------------------------------------------------------------
# Test 5: Role Prompt Loading — content loads and hashes match
# ---------------------------------------------------------------------------

class TestRolePromptLoading:
    """Verify role prompt files load correctly with deterministic hashes."""

    EXPECTED_ROLES = ["builder", "designer", "reviewer_architect", "reviewer_security"]

    def test_all_expected_role_files_exist(self):
        """All expected role prompt files should exist on disk."""
        for role in self.EXPECTED_ROLES:
            path = Path("config/agent_roles") / f"{role}.md"
            assert path.exists(), f"Missing role prompt: {path}"

    def test_role_prompts_load_with_hash(self):
        """Each role prompt should load and produce a sha256 hash."""
        for role in self.EXPECTED_ROLES:
            content, prompt_hash = _load_role_prompt(role)
            assert content, f"Role {role} returned empty content"
            assert prompt_hash.startswith("sha256:"), (
                f"Role {role} hash should start with sha256:"
            )

    def test_role_prompt_hash_matches_file_content(self):
        """Hash from _load_role_prompt should match manual sha256 of file content."""
        for role in self.EXPECTED_ROLES:
            content, prompt_hash = _load_role_prompt(role)
            expected_hash = (
                f"sha256:{hashlib.sha256(content.encode('utf-8')).hexdigest()}"
            )
            assert prompt_hash == expected_hash, (
                f"Role {role} hash mismatch"
            )

    def test_role_prompt_hash_is_stable(self):
        """Loading the same role twice should produce identical hashes."""
        for role in self.EXPECTED_ROLES:
            _, hash1 = _load_role_prompt(role)
            _, hash2 = _load_role_prompt(role)
            assert hash1 == hash2, f"Role {role} hash not stable across loads"

    def test_builder_prompt_contains_expected_content(self):
        """Builder prompt should reference LifeOS Builder Role."""
        content, _ = _load_role_prompt("builder")
        assert "Builder" in content
        assert "LifeOS" in content

    def test_reviewer_architect_prompt_contains_expected_content(self):
        """Reviewer architect prompt should reference architecture review duties."""
        content, _ = _load_role_prompt("reviewer_architect")
        assert "Architect" in content or "architecture" in content.lower()
