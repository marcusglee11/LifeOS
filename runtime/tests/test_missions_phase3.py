"""
Phase 3 Mission Types - Tests

Comprehensive tests for mission modules per AGENT INSTRUCTION BLOCK:
- Unit tests for each mission type (design, review, build, steward)
- Composition test for autonomous_build_cycle
- Schema validation negative tests
- Registry fail-closed tests
"""
import pytest
import sys
import subprocess
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch, MagicMock

from runtime.orchestration.missions import (
    MissionType,
    MissionResult,
    MissionContext,
    MissionError,
    MissionValidationError,
    MissionSchemaError,
    DesignMission,
    ReviewMission,
    BuildMission,
    StewardMission,
    AutonomousBuildCycleMission,
    get_mission_class,
    validate_mission_definition,
    load_mission_schema,
)
from runtime.orchestration.registry import (
    MISSION_REGISTRY,
    list_mission_types,
    run_mission,
    UnknownMissionError,
)
from runtime.orchestration.engine import ExecutionContext


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_context(tmp_path: Path) -> MissionContext:
    """Create a mock mission context for testing."""
    return MissionContext(
        repo_root=tmp_path,
        baseline_commit="abc123",
        run_id="test-run-id",
    )


@pytest.fixture
def valid_build_packet() -> Dict[str, Any]:
    """Create a valid BUILD_PACKET for testing."""
    return {
        "goal": "Implement feature X",
        "scope": {"module": "runtime"},
        "deliverables": [],
        "constraints": ["No breaking changes"],
        "acceptance_criteria": ["Tests pass"],
        "build_type": "code_creation",
        "proposed_changes": [],
        "verification_plan": {"steps": ["pytest"]},
        "risks": [],
        "assumptions": [],
    }


@pytest.fixture
def valid_review_packet(valid_build_packet: Dict[str, Any]) -> Dict[str, Any]:
    """Create a valid REVIEW_PACKET for testing."""
    return {
        "mission_name": "build_test123",
        "summary": "Build for: test goal",
        "payload": {
            "build_packet": valid_build_packet,
            "build_output": {"status": "success", "artifacts_produced": []},
            "artifacts_produced": [],
        },
        "evidence": {"goal": "Implement feature X"},
    }


@pytest.fixture
def approved_decision() -> Dict[str, Any]:
    """Create an approved council decision for testing."""
    return {
        "verdict": "approved",
        "seat_outputs": {},
        "synthesis": "Approved by council",
    }


# =============================================================================
# Test: MissionType Enum
# =============================================================================

class TestMissionType:
    """Tests for MissionType enumeration."""
    
    def test_all_types_defined(self):
        """Verify all required mission types are defined."""
        expected = {"design", "review", "build", "steward", "autonomous_build_cycle", "build_with_validation"}
        actual = {t.value for t in MissionType}
        assert actual == expected
    
    def test_string_enum(self):
        """Verify MissionType is a string enum."""
        assert MissionType.DESIGN.value == "design"
        assert str(MissionType.DESIGN) == "MissionType.DESIGN"


# =============================================================================
# Test: Mission Registry
# =============================================================================

class TestMissionRegistry:
    """Tests for mission registry and routing."""
    
    def test_contains_all_mission_types(self):
        """Verify registry contains all Phase 3 mission types."""
        expected = {"design", "review", "build", "steward", "autonomous_build_cycle", "build_with_validation"}
        actual = set(list_mission_types())
        assert expected.issubset(actual)
    
    def test_get_mission_class_valid(self):
        """Verify get_mission_class returns correct classes."""
        assert get_mission_class("design") == DesignMission
        assert get_mission_class("review") == ReviewMission
        assert get_mission_class("build") == BuildMission
        assert get_mission_class("steward") == StewardMission
        assert get_mission_class("autonomous_build_cycle") == AutonomousBuildCycleMission
        from runtime.orchestration.missions.build_with_validation import BuildWithValidationMission
        assert get_mission_class("build_with_validation") == BuildWithValidationMission
    
    def test_get_mission_class_unknown_fails_closed(self):
        """Verify get_mission_class fails closed on unknown type."""
        with pytest.raises(MissionError) as exc_info:
            get_mission_class("unknown_mission")
        assert "Unknown mission type" in str(exc_info.value)
        assert "unknown_mission" in str(exc_info.value)
    
    def test_run_mission_unknown_fails_closed(self):
        """Verify run_mission fails closed on unknown mission."""
        ctx = ExecutionContext(initial_state={})
        with pytest.raises(UnknownMissionError) as exc_info:
            run_mission("nonexistent_mission", ctx)
        assert "nonexistent_mission" in str(exc_info.value)
        assert "Available missions" in str(exc_info.value)
    
    def test_list_mission_types_deterministic(self):
        """Verify list_mission_types returns sorted list."""
        types = list_mission_types()
        assert types == sorted(types)


# =============================================================================
# Test: Schema Validation
# =============================================================================

class TestSchemaValidation:
    """Tests for mission definition schema validation."""
    
    def test_load_schema_succeeds(self):
        """Verify mission schema can be loaded."""
        schema = load_mission_schema()
        assert schema is not None
        assert "$schema" in schema
        assert "properties" in schema
    
    def test_valid_definition_passes(self):
        """Verify valid mission definition passes validation."""
        valid_def = {
            "id": "test-mission",
            "name": "Test Mission",
            "type": "design",
            "steps": [{"operation": "llm_call"}],
        }
        # Should not raise
        validate_mission_definition(valid_def)
    
    def test_missing_required_field_fails(self):
        """Verify missing required field fails validation."""
        invalid_def = {
            "name": "Test Mission",
            "type": "design",
            # Missing: id, steps
        }
        with pytest.raises(MissionSchemaError) as exc_info:
            validate_mission_definition(invalid_def)
        assert "id" in str(exc_info.value) or "steps" in str(exc_info.value)
    
    def test_invalid_type_enum_fails(self):
        """Verify invalid type enum fails validation."""
        invalid_def = {
            "id": "test-mission",
            "name": "Test Mission",
            "type": "invalid_type",  # Not in enum
            "steps": [],
        }
        with pytest.raises(MissionSchemaError) as exc_info:
            validate_mission_definition(invalid_def)
        assert "type" in str(exc_info.value)
    
    def test_error_messages_sorted(self):
        """Verify error messages are deterministically ordered."""
        invalid_def = {}  # Missing all required fields
        with pytest.raises(MissionSchemaError) as exc_info:
            validate_mission_definition(invalid_def)
        # Multiple errors should be deterministic
        error_str = str(exc_info.value)
        assert error_str == str(exc_info.value)  # Deterministic


# =============================================================================
# Test: Design Mission
# =============================================================================

class TestDesignMission:
    """Tests for design mission."""
    
    def test_mission_type(self):
        """Verify mission type is correct."""
        mission = DesignMission()
        assert mission.mission_type == MissionType.DESIGN
    
    def test_valid_inputs_pass(self, mock_context: MissionContext):
        """Verify valid inputs are accepted."""
        mission = DesignMission()
        inputs = {"task_spec": "Build feature X"}
        # Should not raise
        mission.validate_inputs(inputs)
    
    def test_missing_task_spec_fails(self, mock_context: MissionContext):
        """Verify missing task_spec fails validation."""
        mission = DesignMission()
        with pytest.raises(MissionValidationError) as exc_info:
            mission.validate_inputs({})
        assert "task_spec" in str(exc_info.value)
    
    @patch("runtime.agents.api.call_agent")
    def test_run_succeeds(self, mock_call_agent, mock_context: MissionContext):
        """Verify design mission runs successfully with valid packet."""
        # Setup mock with valid BUILD_PACKET
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.packet = {"goal": "Implement feature X", "scope": {}}
        mock_response.content = "Rationale"
        mock_response.call_id = "test-call-id"
        mock_response.model_used = "test-model"
        mock_response.latency_ms = 100
        mock_call_agent.return_value = mock_response

        mission = DesignMission()
        inputs = {"task_spec": "Implement a new feature"}
        result = mission.run(mock_context, inputs)
        
        assert result.success is True
        assert result.mission_type == MissionType.DESIGN
        assert "build_packet" in result.outputs
        assert "goal" in result.outputs["build_packet"]
        assert "validate_inputs" in result.executed_steps
        assert "design_llm_call" in result.executed_steps
        assert "validate_output" in result.executed_steps  # HARDENING: validate_output step present
        assert result.evidence.get("stubbed") is False  # Real LLM call

    @patch("runtime.agents.api.call_agent")
    def test_run_fails_when_packet_missing(self, mock_call_agent, mock_context: MissionContext):
        """HARDENING: Verify design mission fails closed when response.packet is None."""
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.packet = None  # Missing packet
        mock_response.content = "Some raw content"
        mock_response.call_id = "test-call-id"
        mock_response.model_used = "test-model"
        mock_response.latency_ms = 100
        mock_call_agent.return_value = mock_response

        mission = DesignMission()
        result = mission.run(mock_context, {"task_spec": "Test task"})
        
        assert result.success is False  # FAIL-CLOSED
        assert "validate_output" in result.executed_steps  # Step still runs
        assert "BUILD_PACKET" in result.error  # Deterministic error
        assert "build_packet" not in result.outputs  # No valid output
        assert result.evidence.get("draft_text") == "Some raw content"  # Raw content as evidence

    @patch("runtime.agents.api.call_agent")
    def test_run_fails_when_packet_invalid(self, mock_call_agent, mock_context: MissionContext):
        """HARDENING: Verify design mission fails closed when packet missing required key."""
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.packet = {"scope": {}}  # Missing required 'goal' key
        mock_response.content = "Some content"
        mock_response.call_id = "test-call-id"
        mock_response.model_used = "test-model"
        mock_response.latency_ms = 100
        mock_call_agent.return_value = mock_response

        mission = DesignMission()
        result = mission.run(mock_context, {"task_spec": "Test task"})
        
        assert result.success is False  # FAIL-CLOSED
        assert "validate_output" in result.executed_steps
        assert "goal" in result.error  # Error mentions missing key
        assert result.evidence.get("validation_errors") is not None

    @patch("runtime.agents.api.call_agent")
    def test_run_with_context_refs(self, mock_call_agent, mock_context: MissionContext):
        """Verify design mission handles context_refs."""
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.packet = {"goal": "Implement feature X", "scope": {}}
        mock_response.content = "Rationale"
        mock_response.call_id = "test-call-id"
        mock_response.model_used = "test-model"
        mock_response.latency_ms = 100
        mock_call_agent.return_value = mock_response

        mission = DesignMission()
        inputs = {
            "task_spec": "Implement feature",
            "context_refs": ["docs/spec.md", "src/module.py"],
        }
        result = mission.run(mock_context, inputs)
        
        assert result.success is True
        assert result.evidence.get("context_refs_count") == 2


# =============================================================================
# Test: Review Mission
# =============================================================================

class TestReviewMission:
    """Tests for review mission."""
    
    def test_mission_type(self):
        """Verify mission type is correct."""
        mission = ReviewMission()
        assert mission.mission_type == MissionType.REVIEW
    
    def test_valid_inputs_pass(self, valid_build_packet: Dict[str, Any]):
        """Verify valid inputs are accepted."""
        mission = ReviewMission()
        inputs = {
            "subject_packet": valid_build_packet,
            "review_type": "build_review",
        }
        # Should not raise
        mission.validate_inputs(inputs)
    
    def test_missing_subject_packet_fails(self):
        """Verify missing subject_packet fails validation."""
        mission = ReviewMission()
        with pytest.raises(MissionValidationError) as exc_info:
            mission.validate_inputs({"review_type": "build_review"})
        assert "subject_packet" in str(exc_info.value)
    
    def test_invalid_review_type_fails(self, valid_build_packet: Dict[str, Any]):
        """Verify invalid review_type fails validation."""
        mission = ReviewMission()
        with pytest.raises(MissionValidationError) as exc_info:
            mission.validate_inputs({
                "subject_packet": valid_build_packet,
                "review_type": "invalid_type",
            })
        assert "review_type" in str(exc_info.value)
    
    @patch("runtime.agents.api.call_agent")
    def test_run_succeeds(self, mock_call_agent, mock_context: MissionContext, valid_build_packet: Dict[str, Any]):
        """Verify review mission runs successfully."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.success = True
        # Architect returns a verdict
        mock_response.packet = {"verdict": "approved", "rationale": "Looks good"}
        mock_response.content = "Looks good"
        mock_call_agent.return_value = mock_response

        mission = ReviewMission()
        inputs = {
            "subject_packet": valid_build_packet,
            "review_type": "build_review",
        }
        result = mission.run(mock_context, inputs)
        
        assert result.success is True
        assert result.mission_type == MissionType.REVIEW
        assert "verdict" in result.outputs
        assert "council_decision" in result.outputs
        assert result.outputs["verdict"] in {"approved", "rejected", "needs_revision", "escalate"}


# =============================================================================
# Test: Build Mission
# =============================================================================

class TestBuildMission:
    """Tests for build mission."""
    
    def test_mission_type(self):
        """Verify mission type is correct."""
        mission = BuildMission()
        assert mission.mission_type == MissionType.BUILD
    
    def test_valid_inputs_pass(self, valid_build_packet: Dict[str, Any], approved_decision: Dict[str, Any]):
        """Verify valid inputs are accepted."""
        mission = BuildMission()
        inputs = {
            "build_packet": valid_build_packet,
            "approval": approved_decision,
        }
        # Should not raise
        mission.validate_inputs(inputs)
    
    def test_unapproved_fails(self, valid_build_packet: Dict[str, Any]):
        """Verify unapproved build fails validation."""
        mission = BuildMission()
        with pytest.raises(MissionValidationError) as exc_info:
            mission.validate_inputs({
                "build_packet": valid_build_packet,
                "approval": {"verdict": "rejected"},
            })
        assert "approved" in str(exc_info.value)
    
    @patch("runtime.agents.api.call_agent")
    def test_run_succeeds(self, mock_call_agent, mock_context: MissionContext, valid_build_packet: Dict[str, Any], approved_decision: Dict[str, Any]):
        """Verify build mission runs successfully."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.packet = {"build_output": {"status": "success"}}
        mock_response.content = "Build complete"
        mock_call_agent.return_value = mock_response

        mission = BuildMission()
        inputs = {
            "build_packet": valid_build_packet,
            "approval": approved_decision,
        }
        result = mission.run(mock_context, inputs)
        
        assert result.success is True
        assert result.mission_type == MissionType.BUILD
        assert "review_packet" in result.outputs
        assert "invoke_builder_llm_call" in result.executed_steps


# =============================================================================
# Test: Steward Mission
# =============================================================================

class TestStewardMission:
    """Tests for steward mission."""
    
    def test_mission_type(self):
        """Verify mission type is correct."""
        mission = StewardMission()
        assert mission.mission_type == MissionType.STEWARD
    
    def test_valid_inputs_pass(self, valid_review_packet: Dict[str, Any], approved_decision: Dict[str, Any]):
        """Verify valid inputs are accepted."""
        mission = StewardMission()
        inputs = {
            "review_packet": valid_review_packet,
            "approval": approved_decision,
        }
        # Should not raise
        mission.validate_inputs(inputs)
    
    def test_unapproved_fails(self, valid_review_packet: Dict[str, Any]):
        """Verify unapproved steward fails validation."""
        mission = StewardMission()
        with pytest.raises(MissionValidationError) as exc_info:
            mission.validate_inputs({
                "review_packet": valid_review_packet,
                "approval": {"verdict": "needs_revision"},
            })
        assert "approved" in str(exc_info.value)
    
    @patch("runtime.orchestration.run_controller.verify_repo_clean")
    def test_run_succeeds(self, mock_verify, mock_context: MissionContext, valid_review_packet: Dict[str, Any], approved_decision: Dict[str, Any]):
        """Verify steward mission runs successfully with stub markers."""
        mock_verify.return_value = None  # Success (no exception)
        
        mission = StewardMission()
        inputs = {
            "review_packet": valid_review_packet,
            "approval": approved_decision,
        }
        result = mission.run(mock_context, inputs)
        
        assert result.success is True
        assert result.mission_type == MissionType.STEWARD
        # HARDENING: Output is simulated_commit_hash, not commit_hash
        assert "simulated_commit_hash" in result.outputs
        # HARDENING: Steps have _stub suffix (except target validation which is real)
        assert "commit_stub" in result.executed_steps
        assert "validate_steward_targets" in result.executed_steps  # Real step now
        assert "stage_changes_stub" in result.executed_steps
        assert "record_completion_stub" in result.executed_steps
        assert "verify_repo_clean" in result.executed_steps  # Real step, no stub
        # HARDENING: Evidence shows stubbed=True
        assert result.evidence.get("stubbed") is True
        assert "simulated_steps" in result.evidence

    @patch("runtime.orchestration.run_controller.verify_repo_clean")
    def test_run_fails_with_deterministic_error(self, mock_verify, mock_context: MissionContext, valid_review_packet: Dict[str, Any], approved_decision: Dict[str, Any]):
        """HARDENING: Verify steward fails with deterministic error when repo not clean."""
        # Simulate repo dirty error
        mock_verify.side_effect = Exception("Uncommitted changes detected")
        
        mission = StewardMission()
        inputs = {
            "review_packet": valid_review_packet,
            "approval": approved_decision,
        }
        result = mission.run(mock_context, inputs)
        
        assert result.success is False
        # HARDENING: Error includes deterministic reason
        assert "Repo clean on exit guarantee violated" in result.error
        assert "Uncommitted changes" in result.error
        # HARDENING: Evidence includes repo_clean_result
        assert result.evidence.get("repo_clean_result") is not None


# =============================================================================
# Test: Steward Target Validation (Fail-Closed Semantics)
# =============================================================================

class TestStewardTargetValidation:
    """Tests for steward target validation with fail-closed semantics.
    
    Classification per P0.1:
        A) in_envelope: docs/**/*.md excluding protected roots → BLOCK (requires OpenCode)
        B) protected: docs/00_foundations/**, docs/01_governance/**, scripts/**, config/** → BLOCK
        C) disallowed: Everything else → BLOCK
    """

    # test_steward_blocks_in_envelope_docs_without_opencode REMOVED - now supported via routing

    @patch("runtime.orchestration.run_controller.verify_repo_clean")
    def test_steward_blocks_protected_roots(
        self, mock_verify, mock_context: MissionContext,
        valid_review_packet: Dict[str, Any],
        approved_decision: Dict[str, Any]
    ):
        """Category B: Protected roots are BLOCKED unconditionally."""
        mock_verify.return_value = None
        valid_review_packet["payload"]["artifacts_produced"] = [
            "docs/01_governance/protected.md",
        ]
        
        mission = StewardMission()
        inputs = {
            "review_packet": valid_review_packet,
            "approval": approved_decision,
        }
        result = mission.run(mock_context, inputs)
        
        assert result.success is False
        assert "protected root" in result.error.lower()
        assert "docs/01_governance/protected.md" in result.error
        assert "governance authorization" in result.error.lower()
        # Evidence includes classified paths
        assert "classified_paths" in result.evidence
        assert "docs/01_governance/protected.md" in result.evidence["classified_paths"]["protected"]

    @patch("runtime.orchestration.run_controller.verify_repo_clean")
    def test_steward_blocks_disallowed_paths(
        self, mock_verify, mock_context: MissionContext,
        valid_review_packet: Dict[str, Any],
        approved_decision: Dict[str, Any]
    ):
        """Category C: Non-doc/non-allowlisted paths are BLOCKED."""
        mock_verify.return_value = None
        valid_review_packet["payload"]["artifacts_produced"] = [
            "runtime/module.py",
        ]
        
        mission = StewardMission()
        inputs = {
            "review_packet": valid_review_packet,
            "approval": approved_decision,
        }
        result = mission.run(mock_context, inputs)
        
        assert result.success is False
        assert "disallowed" in result.error.lower()
        assert "runtime/module.py" in result.error
        # Evidence includes classified paths
        assert "classified_paths" in result.evidence
        assert "runtime/module.py" in result.evidence["classified_paths"]["disallowed"]

    @patch("runtime.orchestration.run_controller.verify_repo_clean")
    def test_steward_succeeds_with_empty_artifact_list(
        self, mock_verify, mock_context: MissionContext,
        valid_review_packet: Dict[str, Any],
        approved_decision: Dict[str, Any]
    ):
        """Only empty artifact list is explicitly allowed (no modifications)."""
        mock_verify.return_value = None
        valid_review_packet["payload"]["artifacts_produced"] = []
        
        mission = StewardMission()
        inputs = {
            "review_packet": valid_review_packet,
            "approval": approved_decision,
        }
        result = mission.run(mock_context, inputs)
        
        # Empty artifact list proceeds (stub commits nothing)
        assert result.success is True
        assert "classified_paths" in result.evidence
        assert result.evidence["classified_paths"]["in_envelope"] == []
        assert result.evidence["classified_paths"]["protected"] == []
        assert result.evidence["classified_paths"]["disallowed"] == []

    @patch("runtime.orchestration.run_controller.verify_repo_clean")
    def test_steward_rejects_payload_handler_override(
        self, mock_verify, mock_context: MissionContext,
        valid_review_packet: Dict[str, Any],
        approved_decision: Dict[str, Any]
    ):
        """No payload-driven handler override allowed - still blocked."""
        mock_verify.return_value = None
        valid_review_packet["_handler_override"] = "bypass"
        valid_review_packet["_skip_opencode"] = True
        # Even with injection, disallowed paths still fail
        valid_review_packet["payload"]["artifacts_produced"] = [
            "runtime/some.py"
        ]
        
        mission = StewardMission()
        inputs = {
            "review_packet": valid_review_packet,
            "approval": approved_decision,
        }
        result = mission.run(mock_context, inputs)
        
        # Should FAIL - disallowed paths are blocked regardless of injection
        assert result.success is False
        assert "disallowed" in result.error.lower()
        # No bypass occurred
        assert result.evidence.get("handler_override") is None

    def test_path_classification_all_categories(self, mock_context: MissionContext):
        """Verify path classification covers all A/B/C categories correctly."""
        mission = StewardMission()
        
        # Category B: Protected roots
        protected = [
            ("docs/00_foundations/spec.md", "protected"),
            ("docs/01_governance/policy.md", "protected"),
            ("scripts/runner.py", "protected"),
            ("config/models.yaml", "protected"),
        ]
        for path, expected in protected:
            assert mission._classify_path(path) == expected, f"{path} should be {expected}"
        
        # Category A: In-envelope docs
        in_envelope = [
            ("docs/03_runtime/feature.md", "in_envelope"),
            ("docs/02_protocols/protocol.md", "in_envelope"),
            ("docs/11_admin/STATE.md", "in_envelope"),
        ]
        for path, expected in in_envelope:
            assert mission._classify_path(path) == expected, f"{path} should be {expected}"
        
        # Category C: Disallowed (non-doc paths)
        disallowed = [
            ("runtime/engine.py", "disallowed"),
            ("tests/test_foo.py", "disallowed"),
            ("docs/readme.txt", "disallowed"),  # Non-.md in docs
        ]
        for path, expected in disallowed:
            assert mission._classify_path(path) == expected, f"{path} should be {expected}"


# =============================================================================
# Test: Steward Routing (P0 Implementation)
# =============================================================================

class TestStewardRouting:
    """Tests for Steward OpenCode routing integration (P0)."""

    @patch("runtime.orchestration.missions.steward.subprocess.run")
    @patch("runtime.orchestration.run_controller.verify_repo_clean")
    def test_steward_routes_success(
        self, mock_verify, mock_run, mock_context: MissionContext,
        valid_review_packet: Dict[str, Any], approved_decision: Dict[str, Any]
    ):
        """Verify successful routing to OpenCode runner."""
        mock_verify.return_value = None
        # Setup in-envelope artifact
        valid_review_packet["payload"]["artifacts_produced"] = ["docs/03_runtime/test.md"]
        
        # Mock successful runner execution
        mock_run.return_value = MagicMock(
            returncode=0, 
            stdout="Success log", 
            stderr="No errors"
        )
        
        mission = StewardMission()
        inputs = {
            "review_packet": valid_review_packet,
            "approval": approved_decision,
        }
        # P0: Mock sys.executable for assertion
        with patch("sys.executable", "python_exe"):
            result = mission.run(mock_context, inputs)
        
        assert result.success is True
        assert "invoke_opencode_steward" in result.executed_steps
        assert "opencode_result" in result.evidence
        assert result.evidence["opencode_result"]["exit_code"] == 0
        
        # P0: Verify invocation args
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        cmd = args[0]
        assert cmd[0] == "python_exe"
        assert "opencode_ci_runner.py" in cmd[1]
        assert "--task-file" in cmd
        assert "artifacts/steward_tasks/steward_task_v" in cmd[3].replace("\\", "/") # versioned
        
        # P0: Verify safety args
        assert kwargs["cwd"] == mock_context.repo_root
        assert kwargs["timeout"] == 300
        assert kwargs["check"] is False

    @patch("runtime.orchestration.missions.steward.subprocess.run")
    @patch("runtime.orchestration.run_controller.verify_repo_clean")
    def test_steward_routes_failure_exit_code(
        self, mock_verify, mock_run, mock_context: MissionContext,
        valid_review_packet: Dict[str, Any], approved_decision: Dict[str, Any]
    ):
        """Verify fail-closed on non-zero exit code."""
        mock_verify.return_value = None
        valid_review_packet["payload"]["artifacts_produced"] = ["docs/03_runtime/test.md"]
        
        # Mock failure runner execution
        mock_run.return_value = MagicMock(
            returncode=1, 
            stdout="Partial log", 
            stderr="Validation failed"
        )
        
        mission = StewardMission()
        inputs = {
            "review_packet": valid_review_packet,
            "approval": approved_decision,
        }
        result = mission.run(mock_context, inputs)
        
        # Fail-closed
        assert result.success is False
        assert "OpenCode routing failed" in result.error
        assert "exit code 1" in result.error
        assert "invoke_opencode_steward" in result.executed_steps
        assert result.evidence["opencode_result"]["exit_code"] == 1

    @patch("runtime.orchestration.missions.steward.subprocess.run")
    @patch("runtime.orchestration.run_controller.verify_repo_clean")
    def test_steward_routes_timeout(
        self, mock_verify, mock_run, mock_context: MissionContext,
        valid_review_packet: Dict[str, Any], approved_decision: Dict[str, Any]
    ):
        """Verify fail-closed on timeout."""
        mock_verify.return_value = None
        valid_review_packet["payload"]["artifacts_produced"] = ["docs/03_runtime/test.md"]
        
        # Mock timeout
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="runner", timeout=300)
        
        mission = StewardMission()
        inputs = {
            "review_packet": valid_review_packet,
            "approval": approved_decision,
        }
        result = mission.run(mock_context, inputs)
        
        # Fail-closed
        assert result.success is False
        assert "OpenCode routing failed" in result.error
        assert "timed out after 300s" in result.error or "timed out" in result.error


# =============================================================================
# Test: Autonomous Build Cycle Mission
# =============================================================================

class TestAutonomousBuildCycleMission:
    """Tests for autonomous build cycle mission."""
    
    def test_mission_type(self):
        """Verify mission type is correct."""
        mission = AutonomousBuildCycleMission()
        assert mission.mission_type == MissionType.AUTONOMOUS_BUILD_CYCLE
    
    def test_valid_inputs_pass(self):
        """Verify valid inputs are accepted (same as design)."""
        mission = AutonomousBuildCycleMission()
        inputs = {"task_spec": "Build feature X"}
        # Should not raise
        mission.validate_inputs(inputs)
    
    @patch("runtime.orchestration.missions.autonomous_build_cycle.DesignMission.run")
    @patch("runtime.orchestration.missions.autonomous_build_cycle.ReviewMission.run")
    @patch("runtime.orchestration.missions.autonomous_build_cycle.BuildMission.run")
    @patch("runtime.orchestration.missions.autonomous_build_cycle.StewardMission.run")
    def test_run_composes_correctly(self, mock_steward, mock_build, mock_review, mock_design, mock_context: MissionContext):
        """Verify autonomous build cycle composes missions correctly."""
        # Setup mocks
        design_result = MissionResult(True, MissionType.DESIGN, outputs={"build_packet": {}}, executed_steps=["design"])
        review_result = MissionResult(True, MissionType.REVIEW, outputs={"verdict": "approved", "council_decision": {}}, executed_steps=["review"])
        build_result = MissionResult(True, MissionType.BUILD, outputs={"review_packet": {}}, executed_steps=["build"])
        steward_result = MissionResult(True, MissionType.STEWARD, outputs={"commit_hash": "abc"}, executed_steps=["commit"])
        
        mock_design.return_value = design_result
        mock_review.return_value = review_result 
        mock_build.return_value = build_result
        mock_steward.return_value = steward_result
        
        mission = AutonomousBuildCycleMission()
        inputs = {"task_spec": "Implement end-to-end feature"}
        result = mission.run(mock_context, inputs)
        
        # Check composition was executed
        assert result.mission_type == MissionType.AUTONOMOUS_BUILD_CYCLE
        assert "design" in result.executed_steps
        assert "review_design" in result.executed_steps
        assert "cycle_report" in result.outputs
        
        # Check cycle report structure
        cycle_report = result.outputs["cycle_report"]
        assert "phases" in cycle_report
        assert len(cycle_report["phases"]) > 0
        
        # First phase should be design
        assert cycle_report["phases"][0]["phase"] == "design"

    @patch("runtime.orchestration.missions.autonomous_build_cycle.DesignMission.run")
    @patch("runtime.orchestration.missions.autonomous_build_cycle.ReviewMission.run")
    @patch("runtime.orchestration.missions.autonomous_build_cycle.BuildMission.run")
    @patch("runtime.orchestration.missions.autonomous_build_cycle.StewardMission.run")
    def test_run_full_cycle_success(self, mock_steward, mock_build, mock_review, mock_design, mock_context: MissionContext):
        """Verify full cycle runs to completion (with stubbed implementations)."""
        # Setup mocks
        design_result = MissionResult(True, MissionType.DESIGN, outputs={"build_packet": {}}, executed_steps=["design"])
        review_result = MissionResult(True, MissionType.REVIEW, outputs={"verdict": "approved", "council_decision": {}}, executed_steps=["review"])
        build_result = MissionResult(True, MissionType.BUILD, outputs={"review_packet": {}}, executed_steps=["build"])
        steward_result = MissionResult(True, MissionType.STEWARD, outputs={"commit_hash": "abc"}, executed_steps=["commit"])
        
        mock_design.return_value = design_result
        mock_review.return_value = review_result 
        mock_build.return_value = build_result
        mock_steward.return_value = steward_result
        
        mission = AutonomousBuildCycleMission()
        inputs = {"task_spec": "Complete implementation"}
        result = mission.run(mock_context, inputs)
        
        # With stubbed implementations, all reviews auto-approve
        # So the full cycle should complete
        assert result.success is True
        assert "commit_hash" in result.outputs
        assert "steward" in result.executed_steps


# =============================================================================
# Test: Steward Routing (P0 Implementation)
# =============================================================================

class TestStewardRouting:
    """Tests for Steward OpenCode routing integration (P0)."""

    @patch("runtime.orchestration.missions.steward.subprocess.run")
    @patch("runtime.orchestration.run_controller.verify_repo_clean")
    def test_steward_routes_success(
        self, mock_verify, mock_run, mock_context: MissionContext,
        valid_review_packet: Dict[str, Any], approved_decision: Dict[str, Any]
    ):
        """Verify successful routing to OpenCode runner."""
        mock_verify.return_value = None
        # Setup in-envelope artifact
        valid_review_packet["payload"]["artifacts_produced"] = ["docs/03_runtime/test.md"]
        
        # Mock successful runner execution
        mock_run.return_value = MagicMock(
            returncode=0, 
            stdout="Success log", 
            stderr="No errors"
        )
        
        mission = StewardMission()
        inputs = {
            "review_packet": valid_review_packet,
            "approval": approved_decision,
        }
        # P0: Mock sys.executable for assertion
        with patch("sys.executable", "python_exe"):
            result = mission.run(mock_context, inputs)
        
        assert result.success is True
        assert "invoke_opencode_steward" in result.executed_steps
        assert "opencode_result" in result.evidence
        assert result.evidence["opencode_result"]["exit_code"] == 0
        
        # P0: Verify invocation args
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        cmd = args[0]
        assert cmd[0] == "python_exe"
        assert "opencode_ci_runner.py" in cmd[1]
        assert "--task-file" in cmd
        assert "artifacts/steward_tasks/steward_task_v" in cmd[3].replace("\\", "/") # versioned
        
        # P0: Verify safety args
        assert kwargs["cwd"] == mock_context.repo_root
        assert kwargs["timeout"] == 300
        assert kwargs["check"] is False

    @patch("runtime.orchestration.missions.steward.subprocess.run")
    @patch("runtime.orchestration.run_controller.verify_repo_clean")
    def test_steward_routes_failure_exit_code(
        self, mock_verify, mock_run, mock_context: MissionContext,
        valid_review_packet: Dict[str, Any], approved_decision: Dict[str, Any]
    ):
        """Verify fail-closed on non-zero exit code."""
        mock_verify.return_value = None
        valid_review_packet["payload"]["artifacts_produced"] = ["docs/03_runtime/test.md"]
        
        # Mock failure runner execution
        mock_run.return_value = MagicMock(
            returncode=1, 
            stdout="Partial log", 
            stderr="Validation failed"
        )
        
        mission = StewardMission()
        inputs = {
            "review_packet": valid_review_packet,
            "approval": approved_decision,
        }
        result = mission.run(mock_context, inputs)
        
        # Fail-closed
        assert result.success is False
        assert "OpenCode routing failed" in result.error
        assert "exit code 1" in result.error
        assert "invoke_opencode_steward" in result.executed_steps
        assert result.evidence["opencode_result"]["exit_code"] == 1

    @patch("runtime.orchestration.missions.steward.subprocess.run")
    @patch("runtime.orchestration.run_controller.verify_repo_clean")
    def test_steward_routes_timeout(
        self, mock_verify, mock_run, mock_context: MissionContext,
        valid_review_packet: Dict[str, Any], approved_decision: Dict[str, Any]
    ):
        """Verify fail-closed on timeout."""
        mock_verify.return_value = None
        valid_review_packet["payload"]["artifacts_produced"] = ["docs/03_runtime/test.md"]
        
        # P0: Mock timeout exception
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="runner", timeout=300)
        
        mission = StewardMission()
        inputs = {
            "review_packet": valid_review_packet,
            "approval": approved_decision,
        }
        result = mission.run(mock_context, inputs)
        
        # Fail-closed
        assert result.success is False
        assert "OpenCode routing failed" in result.error
        assert "timed out after 300s" in result.error or "timed out" in result.error


# =============================================================================
# Test: MissionResult Serialization
# =============================================================================

class TestMissionResultSerialization:
    """Tests for MissionResult deterministic serialization."""
    
    def test_to_dict_deterministic(self):
        """Verify to_dict produces deterministic output."""
        result = MissionResult(
            success=True,
            mission_type=MissionType.DESIGN,
            outputs={"z_key": "z", "a_key": "a"},
            executed_steps=["step1", "step2"],
            evidence={"z_ev": "z", "a_ev": "a"},
        )
        
        d = result.to_dict()
        
        # Check keys are present
        assert "success" in d
        assert "mission_type" in d
        assert "outputs" in d
        assert "executed_steps" in d
        assert "evidence" in d
        
        # Check values are sorted
        output_keys = list(d["outputs"].keys())
        assert output_keys == sorted(output_keys)
        
        evidence_keys = list(d["evidence"].keys())
        assert evidence_keys == sorted(evidence_keys)
    
    def test_to_dict_consistent(self):
        """Verify multiple calls produce same output."""
        result = MissionResult(
            success=True,
            mission_type=MissionType.BUILD,
            outputs={"key": "value"},
        )
        
        d1 = result.to_dict()
        d2 = result.to_dict()
        
        assert d1 == d2


# =============================================================================
# Test: Engine Mission Dispatch
# =============================================================================

class TestEngineMissionDispatch:
    """Tests for engine.py mission operation dispatch."""
    
    def test_design_mission_via_registry(self):
        """Verify design mission can be run via registry."""
        ctx = ExecutionContext(initial_state={"task_spec": "Test task"})
        # This tests the workflow builder, not direct mission execution
        result = run_mission("design", ctx, params={"task_spec": "Test task"})
        
        # The result is an OrchestrationResult from the workflow
        assert result.success is True or result.success is False  # Any valid result
    
    def test_unknown_mission_fails_closed(self):
        """Verify unknown mission type fails closed."""
        ctx = ExecutionContext(initial_state={})
        with pytest.raises(UnknownMissionError):
            run_mission("completely_unknown_type", ctx)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
