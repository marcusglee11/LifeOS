"""
E2E Tests for Policy Engine Authoritative Gating.

Per Agent Instruction Block - validates end-to-end wiring for promoting
Policy Engine to authoritative gating, covering:
- E2E-1: Authoritative ON uses Policy Engine with rule application (not Phase A fallback)
- E2E-2: Authoritative OFF falls back to Phase A deterministically
- E2E-3: Invalid/unverifiable config fails closed
- E2E-4: Filesystem scope via ToolRegistry.dispatch() (real tool execution path)
- E2E-5: Escalation artifact determinism + unresolvable write fails closed (2 tests)
- E2E-6a: Valid waiver artifact resumes execution (WAIVER_APPLIED)
- E2E-6b: Expired waiver artifact fails closed (WAIVER_REQUESTED)
"""

import pytest
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock

from runtime.orchestration.loop.policy import LoopPolicy, ConfigDrivenLoopPolicy, EscalationArtifact
from runtime.governance.policy_loader import PolicyLoader, PolicyLoadError
from runtime.governance.tool_policy import check_tool_action_allowed
from runtime.tools.schemas import ToolInvokeRequest, ToolErrorType
from runtime.tools.registry import ToolRegistry, get_registry, reset_global_registry
from runtime.orchestration.loop.ledger import AttemptLedger, AttemptRecord, LedgerHeader
from runtime.orchestration.loop.taxonomy import FailureClass


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def policy_config_dir(tmp_path):
    """Create temporary policy config directory with valid/invalid configs."""
    config_dir = tmp_path / "config" / "policy"
    config_dir.mkdir(parents=True)
    
    # Valid config (minimal - PolicyLoader only allows schema_version and includes)
    valid_config = """
schema_version: "1.0"
includes: []
"""
    (config_dir / "policy_rules.yaml").write_text(valid_config)
    
    # Schema file (minimal)
    schema = {"type": "object", "properties": {"schema_version": {"type": "string"}}}
    (config_dir / "policy_schema.json").write_text(json.dumps(schema))
    
    return config_dir


@pytest.fixture
def policy_config_dir_with_loop_rules(tmp_path):
    """Create policy config directory with loop_rules for E2E-1 wiring test."""
    config_dir = tmp_path / "config" / "policy"
    config_dir.mkdir(parents=True)
    
    # Master config with includes pointing to loop_rules file
    master_config = """
schema_version: "1.0"
includes:
  - loop_rules.yaml
"""
    (config_dir / "policy_rules.yaml").write_text(master_config)
    
    # Separate loop_rules file (PolicyLoader expects list format)
    loop_rules_content = """
- rule_id: "e2e1_wiring_rule"
  match:
    failure_class: "E2E1_TEST_CLASS"
  decision: "TERMINATE"
  priority: 100
  on_match:
    terminal_reason: "E2E1_WIRING_VERIFIED"
"""
    (config_dir / "loop_rules.yaml").write_text(loop_rules_content)
    
    # Schema file (minimal)
    schema = {"type": "object", "properties": {"schema_version": {"type": "string"}}}
    (config_dir / "policy_schema.json").write_text(json.dumps(schema))
    
    return config_dir


@pytest.fixture
def mock_ledger_empty(tmp_path):
    """Empty ledger for start-of-run tests."""
    ledger_path = tmp_path / "empty_ledger.jsonl"
    ledger = AttemptLedger(ledger_path)
    return ledger


@pytest.fixture
def mock_ledger_with_attempts(tmp_path):
    """Ledger with attempts for policy decision tests."""
    ledger_path = tmp_path / "ledger.jsonl"
    ledger = AttemptLedger(ledger_path)
    
    header = LedgerHeader(
        policy_hash="test_policy_v1",
        handoff_hash="test_handoff",
        run_id="test_run_123"
    )
    ledger.initialize(header)
    
    return ledger


@pytest.fixture
def sandbox_environment(tmp_path, monkeypatch):
    """Set up sandbox environment for tool execution tests."""
    sandbox_root = tmp_path / "sandbox"
    sandbox_root.mkdir()
    
    monkeypatch.setenv("LIFEOS_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("LIFEOS_SANDBOX_ROOT", str(sandbox_root))
    
    # Reset global registry to pick up new sandbox
    reset_global_registry()
    
    return sandbox_root


# =============================================================================
# E2E-1: Authoritative ON uses Policy Engine AND Phase A NOT used
# =============================================================================

def test_e2e_1_authoritative_on_uses_policy_engine(policy_config_dir_with_loop_rules, tmp_path, monkeypatch):
    """E2E-1: Authoritative ON uses config-driven policy with rule application.
    
    Validates:
    - ConfigDrivenLoopPolicy is instantiated
    - Phase A (_hardcoded_decide) is NOT called
    - Configured rule is applied to matching ledger state
    """
    
    # Arrange: Set workspace root and load config in authoritative mode
    monkeypatch.setenv("LIFEOS_WORKSPACE_ROOT", str(policy_config_dir_with_loop_rules.parent.parent))
    
    loader = PolicyLoader(config_dir=policy_config_dir_with_loop_rules, authoritative=True)
    effective_config = loader.load()
    
    # Create LoopPolicy with effective config (authoritative mode)
    policy = LoopPolicy(effective_config=effective_config)
    
    # Assert 1: ConfigDrivenLoopPolicy is instantiated (wiring verified)
    assert policy._config_policy is not None, "Config-driven policy should be instantiated when loop_rules present"
    assert isinstance(policy._config_policy, ConfigDrivenLoopPolicy), "_config_policy should be ConfigDrivenLoopPolicy instance"
    
    # Arrange: Create ledger with attempt matching the seeded rule (failure_class: E2E1_TEST_CLASS)
    ledger_path = tmp_path / "e2e1_ledger.jsonl"
    ledger = AttemptLedger(ledger_path)
    header = LedgerHeader(policy_hash="test", handoff_hash="test", run_id="test_e2e1")
    ledger.initialize(header)
    
    # Add attempt with matching failure_class
    record = AttemptRecord(
        attempt_id=1,
        timestamp="2026-01-23T00:00:00Z",
        run_id="test_e2e1",
        policy_hash="test",
        input_hash="test",
        actions_taken=[],
        diff_hash="hash1",
        changed_files=[],
        evidence_hashes={},
        success=False,
        failure_class="E2E1_TEST_CLASS",  # Matches rule in loop_rules.yaml
        terminal_reason=None,
        next_action="retry",
        rationale="test"
    )
    ledger.append(record)
    
    # Spy on _hardcoded_decide to prove it is NOT called
    with patch.object(policy, '_hardcoded_decide', wraps=policy._hardcoded_decide) as mock_hardcoded:
        # Also spy on config-driven policy to prove it IS called
        with patch.object(policy._config_policy, 'decide_next_action', wraps=policy._config_policy.decide_next_action) as mock_config:
            action, reason = policy.decide_next_action(ledger)
            
            # Assert: _hardcoded_decide was NOT called
            assert not mock_hardcoded.called, "_hardcoded_decide should NOT be called when config-driven policy is active"
            
            # Assert: config-driven policy WAS called
            assert mock_config.called, "ConfigDrivenLoopPolicy.decide_next_action should be called"
            
            # Assert: Rule was applied (E2E1_TEST_CLASS rule returns TERMINATE with E2E1_WIRING_VERIFIED)
            assert action == "terminate", f"Expected terminate from rule, got {action}"
            assert "E2E1_WIRING_VERIFIED" in reason, f"Expected E2E1_WIRING_VERIFIED in reason, got {reason}"


# =============================================================================
# E2E-2: Authoritative OFF falls back to Phase A
# =============================================================================

def test_e2e_2_authoritative_off_fallback_phase_a(mock_ledger_empty):
    """E2E-2: Authoritative OFF falls back to Phase A deterministically."""
    
    # Arrange: Create LoopPolicy without config (Phase A mode)
    policy = LoopPolicy()  # No effective_config = Phase A fallback
    
    # Spy on _hardcoded_decide
    with patch.object(policy, '_hardcoded_decide', wraps=policy._hardcoded_decide) as mock_hardcoded:
        # Act: Invoke decision
        action, reason = policy.decide_next_action(mock_ledger_empty)
        
        # Assert: _hardcoded_decide was called
        assert mock_hardcoded.called, "_hardcoded_decide should be called when no config provided"
        assert action == "retry"  # Start action per Phase A logic
        assert policy._config_policy is None, "No config policy should be instantiated"


# =============================================================================
# E2E-3: Invalid/unverifiable config fails closed
# =============================================================================

def test_e2e_3_invalid_config_fails_closed(tmp_path, monkeypatch):
    """E2E-3: Invalid/unverifiable config fails closed (no best-effort)."""
    
    # Arrange: Set workspace root and create INVALID config
    config_dir = tmp_path / "config" / "policy"
    config_dir.mkdir(parents=True)
    
    # Invalid YAML (malformed)
    (config_dir / "policy_rules.yaml").write_text("invalid: yaml: [[[")
    
    monkeypatch.setenv("LIFEOS_WORKSPACE_ROOT", str(tmp_path))
    
    # Act & Assert: Loading should raise PolicyLoadError in authoritative mode
    loader = PolicyLoader(config_dir=config_dir, authoritative=True)
    
    with pytest.raises(PolicyLoadError):
        loader.load()


# =============================================================================
# E2E-4: Filesystem scope via ToolRegistry.dispatch() (real tool path)
# =============================================================================

def test_e2e_4_filesystem_scope_via_dispatch(sandbox_environment, tmp_path, monkeypatch):
    """E2E-4: Filesystem scope enforced via ToolRegistry.dispatch() with real writes."""
    
    # Arrange: Get registry with builtins registered
    registry = get_registry(sandbox_root=sandbox_environment)
    
    # Subcase A: Missing path - DENY
    request_missing = ToolInvokeRequest.from_dict({
        "tool": "filesystem",
        "action": "write_file",
        "args": {"content": "test content"}  # No path
    })
    
    result_missing = registry.dispatch(request_missing)
    
    assert result_missing.error is not None, "Missing path should result in error"
    assert result_missing.error.type == ToolErrorType.POLICY_DENIED
    assert "path" in result_missing.error.message.lower()
    
    # Subcase B: Out-of-scope path - DENY
    request_out = ToolInvokeRequest.from_dict({
        "tool": "filesystem",
        "action": "write_file",
        "args": {"path": "../outside.txt", "content": "test content"}
    })
    
    result_out = registry.dispatch(request_out)
    
    assert result_out.error is not None, "Out-of-scope path should result in error"
    assert result_out.error.type == ToolErrorType.POLICY_DENIED

    
    # Subcase C: In-scope path - ALLOW and actual write occurs
    test_file = sandbox_environment / "e2e4_test.txt"
    request_in = ToolInvokeRequest.from_dict({
        "tool": "filesystem",
        "action": "write_file",
        "args": {"path": str(test_file), "content": "E2E-4 test content"}
    })
    
    result_in = registry.dispatch(request_in)
    
    assert result_in.error is None, f"In-scope write should succeed: {result_in.error}"
    assert result_in.policy.allowed is True
    
    # Assert: File was actually created with expected content
    assert test_file.exists(), "File should be created on disk"
    assert test_file.read_text() == "E2E-4 test content", "File content should match"


# =============================================================================
# E2E-5: Escalation artifact determinism + unresolvable write fails closed
# =============================================================================

def test_e2e_5_escalation_artifact_determinism(tmp_path, policy_config_dir, mock_ledger_with_attempts, monkeypatch):
    """E2E-5: Escalation artifact is written and contains required fields."""
    
    # Arrange: Redirect artifact directory to tmp_path
    artifact_dir = tmp_path / "artifacts" / "escalations" / "Policy_Engine"
    monkeypatch.setattr(EscalationArtifact, "ARTIFACT_DIR", artifact_dir)
    
    monkeypatch.setenv("LIFEOS_WORKSPACE_ROOT", str(policy_config_dir.parent.parent))
    
    # Load config with escalation triggers
    from runtime.orchestration.loop.configurable_policy import ConfigurableLoopPolicy
    
    config_data = {
        "budgets": {"retry_limits": {"REVIEW_REJECTION": 3}},
        "failure_routing": {"REVIEW_REJECTION": {"default_action": "RETRY"}},
        "waiver_rules": {
            "eligible_failure_classes": ["REVIEW_REJECTION"],
            "escalation_triggers": ["protected_path"]
        },
        "progress_detection": {}
    }
    
    policy = ConfigurableLoopPolicy(config_data)
    
    # Add 3 failures to exhaust retry budget with protected path
    for i in range(3):
        record = AttemptRecord(
            attempt_id=i+1,
            timestamp=f"2026-01-23T00:0{i}:00Z",
            run_id="test_run",
            policy_hash="test",
            input_hash="test",
            actions_taken=[],
            diff_hash=f"hash{i}",
            changed_files=["docs/01_governance/test.md"],  # Protected path
            evidence_hashes={},
            success=False,
            failure_class="REVIEW_REJECTION",
            terminal_reason=None,
            next_action="retry",
            rationale="test"
        )
        mock_ledger_with_attempts.append(record)
    
    # Act: Invoke policy decision (triggers escalation)
    action, reason, override = policy.decide_next_action(mock_ledger_with_attempts)
    
    # Assert: Escalation signal is returned
    assert action == "terminate"
    assert override == "ESCALATION_REQUESTED"
    assert "escalation" in reason.lower()
    
    # Act: Write escalation artifact
    artifact_path = EscalationArtifact.write(
        reason=reason,
        requested_authority="CEO",
        ttl_seconds=3600,
        context={"failure_class": "REVIEW_REJECTION"}
    )
    
    # Assert: Artifact exists and contains required fields
    assert artifact_path.exists(), "Escalation artifact should be written"
    
    artifact_content = json.loads(artifact_path.read_text())
    assert "reason" in artifact_content
    assert "requested_authority" in artifact_content
    assert artifact_content["requested_authority"] == "CEO"
    assert "ttl_seconds" in artifact_content
    assert "created_at" in artifact_content


def test_e2e_5_unresolvable_escalation_write_fails_closed(tmp_path, monkeypatch):
    """E2E-5 (variant): Unresolvable escalation artifact write fails closed."""
    
    # Arrange: Make artifact directory unwritable
    artifact_dir = tmp_path / "artifacts" / "escalations" / "Policy_Engine"
    monkeypatch.setattr(EscalationArtifact, "ARTIFACT_DIR", artifact_dir)
    
    # Create parent but make it read-only (simulate unwritable)
    artifact_dir.parent.mkdir(parents=True, exist_ok=True)
    
    # Patch open to raise permission error
    original_open = open
    def mock_open(*args, **kwargs):
        if "ESCALATION_" in str(args[0]) if args else "":
            raise PermissionError("Cannot write to artifact directory")
        return original_open(*args, **kwargs)
    
    with patch("builtins.open", side_effect=mock_open):
        # Act & Assert: Write should raise exception (fail-closed)
        with pytest.raises(PermissionError):
            EscalationArtifact.write(
                reason="Test escalation",
                requested_authority="CEO"
            )


# =============================================================================
# E2E-6: Waiver artifact behavior + TTL (true end-to-end)
# =============================================================================

def test_e2e_6a_valid_waiver_resumes(tmp_path, mock_ledger_with_attempts, monkeypatch):
    """E2E-6a: Valid waiver artifact causes retry to resume (not terminate)."""
    from datetime import datetime, timezone, timedelta
    from runtime.orchestration.loop.configurable_policy import ConfigurableLoopPolicy
    from runtime.orchestration.loop import waiver_artifact
    
    # Arrange: Fixed time for deterministic testing
    fixed_now = datetime(2026, 1, 23, 10, 0, 0, tzinfo=timezone.utc)
    
    # Redirect waiver artifact directory to tmp_path
    waiver_dir = tmp_path / "artifacts" / "waivers" / "Policy_Engine"
    monkeypatch.setattr(waiver_artifact, "WAIVER_ARTIFACT_DIR", waiver_dir)
    
    config_data = {
        "budgets": {"retry_limits": {"REVIEW_REJECTION": 3}},
        "failure_routing": {"REVIEW_REJECTION": {"default_action": "RETRY"}},
        "waiver_rules": {
            "eligible_failure_classes": ["REVIEW_REJECTION"],
            "ineligible_failure_classes": []
        },
        "progress_detection": {}
    }
    
    policy = ConfigurableLoopPolicy(config_data)
    
    # Add 3 consecutive failures (exhaust retry limit) - NO protected paths
    for i in range(3):
        record = AttemptRecord(
            attempt_id=i+1,
            timestamp=f"2026-01-23T00:0{i}:00Z",
            run_id="test_run",
            policy_hash="test",
            input_hash="test",
            actions_taken=[],
            diff_hash=f"hash{i}",
            changed_files=[],  # No protected paths = no escalation
            evidence_hashes={},
            success=False,
            failure_class="REVIEW_REJECTION",
            terminal_reason=None,
            next_action="retry",
            rationale="test"
        )
        mock_ledger_with_attempts.append(record)
    
    # Build waiver context matching what ConfigurableLoopPolicy uses
    waiver_context = {
        "failure_class": "REVIEW_REJECTION",
        "retry_count": 3,
        "retry_limit": 3
    }
    
    # Write valid waiver artifact (expires in 1 hour from fixed_now)
    waiver_grant = waiver_artifact.WaiverGrant.create(
        granted_by="CEO",
        reason="Test waiver for E2E-6a",
        context=waiver_context,
        ttl_seconds=3600,  # 1 hour
        now=fixed_now
    )
    
    artifact_path = waiver_artifact.get_waiver_path(waiver_context, base_dir=waiver_dir)
    waiver_artifact.write(artifact_path, waiver_grant)
    
    # Act: Invoke policy decision with fixed time (waiver is valid)
    action, reason, override = policy.decide_next_action(mock_ledger_with_attempts, now=fixed_now)
    
    # Assert: Waiver applied, execution resumes
    assert action == "retry", f"Expected retry (waiver applied), got {action}"
    assert override == "WAIVER_APPLIED", f"Expected WAIVER_APPLIED, got {override}"
    assert "waiver applied" in reason.lower()


def test_e2e_6b_expired_waiver_fails_closed(tmp_path, mock_ledger_with_attempts, monkeypatch):
    """E2E-6b: Expired waiver artifact causes WAIVER_REQUESTED (fail-closed)."""
    from datetime import datetime, timezone, timedelta
    from runtime.orchestration.loop.configurable_policy import ConfigurableLoopPolicy
    from runtime.orchestration.loop import waiver_artifact
    
    # Arrange: Fixed time for deterministic testing (waiver expired 1 minute ago)
    fixed_now = datetime(2026, 1, 23, 11, 1, 0, tzinfo=timezone.utc)
    waiver_granted_at = datetime(2026, 1, 23, 10, 0, 0, tzinfo=timezone.utc)
    
    # Redirect waiver artifact directory to tmp_path
    waiver_dir = tmp_path / "artifacts" / "waivers" / "Policy_Engine"
    monkeypatch.setattr(waiver_artifact, "WAIVER_ARTIFACT_DIR", waiver_dir)
    
    config_data = {
        "budgets": {"retry_limits": {"REVIEW_REJECTION": 3}},
        "failure_routing": {"REVIEW_REJECTION": {"default_action": "RETRY"}},
        "waiver_rules": {
            "eligible_failure_classes": ["REVIEW_REJECTION"],
            "ineligible_failure_classes": []
        },
        "progress_detection": {}
    }
    
    policy = ConfigurableLoopPolicy(config_data)
    
    # Add 3 consecutive failures (exhaust retry limit)
    for i in range(3):
        record = AttemptRecord(
            attempt_id=i+1,
            timestamp=f"2026-01-23T00:0{i}:00Z",
            run_id="test_run",
            policy_hash="test",
            input_hash="test",
            actions_taken=[],
            diff_hash=f"hash{i}",
            changed_files=[],
            evidence_hashes={},
            success=False,
            failure_class="REVIEW_REJECTION",
            terminal_reason=None,
            next_action="retry",
            rationale="test"
        )
        mock_ledger_with_attempts.append(record)
    
    # Build waiver context
    waiver_context = {
        "failure_class": "REVIEW_REJECTION",
        "retry_count": 3,
        "retry_limit": 3
    }
    
    # Write EXPIRED waiver artifact (1 hour TTL, but now is 1 hour + 1 minute later)
    waiver_grant = waiver_artifact.WaiverGrant.create(
        granted_by="CEO",
        reason="Expired test waiver for E2E-6b",
        context=waiver_context,
        ttl_seconds=3600,  # 1 hour
        now=waiver_granted_at  # Granted at 10:00, expires at 11:00
    )
    
    artifact_path = waiver_artifact.get_waiver_path(waiver_context, base_dir=waiver_dir)
    waiver_artifact.write(artifact_path, waiver_grant)
    
    # Act: Invoke policy decision with fixed time (waiver is expired)
    action, reason, override = policy.decide_next_action(mock_ledger_with_attempts, now=fixed_now)
    
    # Assert: Waiver expired, WAIVER_REQUESTED returned (fail-closed)
    assert action == "terminate", f"Expected terminate (expired waiver), got {action}"
    assert override == "WAIVER_REQUESTED", f"Expected WAIVER_REQUESTED, got {override}"
    assert "waiver requested" in reason.lower()

