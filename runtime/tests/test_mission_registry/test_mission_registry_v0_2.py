"""
Mission Registry v0.2 — TDD Test Suite (RED phase)

Tests for v0.2 synthesis + validation:
- Deterministic synthesis: same input → identical output
- Schema validation: required fields present
- Invariant validation: 5+ invalid cases rejected
- Error taxonomy: stable, typed errors
- Golden fixture: determinism proof
"""
import json
import pytest

from runtime.mission import (
    MissionId,
    MissionDefinition,
    MissionRegistryState,
    MissionBoundaryViolation,
    MissionBoundaryConfig,
    canonical_json,
    state_hash,
)

# v0.2 imports — these will fail until implemented
from runtime.mission import (
    MissionSynthesisRequest,
    MissionSynthesisRequest,
    synthesize_mission,
    validate_mission_definition_v0_2,
)


# =============================================================================
# Golden Fixture for Determinism Proof
# =============================================================================

GOLDEN_REQUEST = {
    "id": "test-001",
    "name": "Golden Test Mission",
    "description": "A deterministic test case",
    "tags": ("core", "test"),
    "metadata": {"author": "antigravity", "priority": "high"},
}

# Expected canonical JSON hash for the golden fixture
# This will be computed once and checked in for determinism proof
GOLDEN_HASH = None  # To be set after first successful synthesis


# =============================================================================
# Cycle 1: v0.2 Public API
# =============================================================================

class TestCycle1V02PublicAPI:
    """Cycle 1: v0.2 module exports new symbols."""
    
    def test_synthesis_request_is_exported(self):
        """MissionSynthesisRequest is importable from runtime.mission."""
        assert MissionSynthesisRequest is not None
    
    def test_synthesize_mission_is_exported(self):
        """synthesize_mission function is importable from runtime.mission."""
        assert synthesize_mission is not None
        assert callable(synthesize_mission)
    
    def test_validate_mission_definition_v02_is_exported(self):
        """v0.2 explicit validator is importable."""
        assert validate_mission_definition_v0_2 is not None
        assert callable(validate_mission_definition_v0_2)
    
    def test_ambiguous_validate_names_are_not_exported(self):
        """Generic 'validate' and old 'validate_mission' are NOT exported."""
        with pytest.raises(ImportError):
            from runtime.mission import validate
        
        with pytest.raises(ImportError):
            from runtime.mission import validate_mission


# =============================================================================
# Cycle 2: MissionSynthesisRequest Schema
# =============================================================================

class TestCycle2SynthesisRequestSchema:
    """Cycle 2: MissionSynthesisRequest has correct structure."""
    
    def test_synthesis_request_has_required_fields(self):
        """MissionSynthesisRequest has id, name, description, tags, metadata."""
        req = MissionSynthesisRequest(
            id="test-id",
            name="Test Name",
            description="Test description",
            tags=("tag1", "tag2"),
            metadata={"key": "value"},
        )
        assert req.id == "test-id"
        assert req.name == "Test Name"
        assert req.description == "Test description"
        assert req.tags == ("tag1", "tag2")
        assert req.metadata == {"key": "value"}
    
    def test_synthesis_request_defaults(self):
        """MissionSynthesisRequest has sensible defaults."""
        req = MissionSynthesisRequest(id="test-id", name="Test Name")
        assert req.description == ""
        assert req.tags == ()
        assert req.metadata is None or req.metadata == {}
    
    def test_synthesis_request_is_frozen(self):
        """MissionSynthesisRequest is immutable."""
        req = MissionSynthesisRequest(id="test-id", name="Test Name")
        with pytest.raises(Exception):  # FrozenInstanceError
            req.id = "changed"


# =============================================================================
# Cycle 3: Deterministic Synthesis
# =============================================================================

class TestCycle3DeterministicSynthesis:
    """Cycle 3: synthesize_mission produces identical output for same input."""
    
    def test_synthesis_produces_mission_definition(self):
        """synthesize_mission returns a MissionDefinition."""
        req = MissionSynthesisRequest(id="syn-test", name="Synthesis Test")
        result = synthesize_mission(req)
        assert isinstance(result, MissionDefinition)
    
    def test_synthesis_is_deterministic(self):
        """Same request produces identical MissionDefinition."""
        req = MissionSynthesisRequest(
            id="det-test",
            name="Determinism Test",
            description="Testing determinism",
            tags=("a", "b"),
            metadata={"key": "value"},
        )
        result1 = synthesize_mission(req)
        result2 = synthesize_mission(req)
        
        # Same object equality
        assert result1 == result2
        
        # Same hash (via state)
        state1 = MissionRegistryState(missions=(result1,))
        state2 = MissionRegistryState(missions=(result2,))
        assert state_hash(state1) == state_hash(state2)
    
    def test_synthesis_canonical_json_is_stable(self):
        """Synthesized mission produces stable canonical JSON."""
        req = MissionSynthesisRequest(
            id="json-test",
            name="JSON Test",
            tags=("x", "y"),
        )
        result = synthesize_mission(req)
        state = MissionRegistryState(missions=(result,))
        
        json1 = canonical_json(state)
        json2 = canonical_json(state)
        
        assert json1 == json2
    
    def test_synthesis_metadata_sorted_by_key(self):
        """Metadata in synthesized mission is sorted by key."""
        req = MissionSynthesisRequest(
            id="meta-test",
            name="Metadata Test",
            metadata={"zebra": "z", "alpha": "a", "middle": "m"},
        )
        result = synthesize_mission(req)
        
        # to_dict should have sorted metadata
        d = result.to_dict()
        meta_keys = list(d["metadata"].keys())
        assert meta_keys == sorted(meta_keys)


# =============================================================================
# Cycle 4: Invariant Validation (5+ invalid cases)
# =============================================================================

class TestCycle4InvariantValidation:
    """Cycle 4: synthesize_mission rejects invalid inputs."""
    
    def test_rejects_empty_id(self):
        """Empty ID raises MissionBoundaryViolation."""
        req = MissionSynthesisRequest(id="", name="Valid Name")
        with pytest.raises(MissionBoundaryViolation, match="Mission ID.*empty|must not be empty"):
            synthesize_mission(req)
    
    def test_rejects_whitespace_only_id(self):
        """Whitespace-only ID raises MissionBoundaryViolation."""
        req = MissionSynthesisRequest(id="   ", name="Valid Name")
        with pytest.raises(MissionBoundaryViolation, match="Mission ID.*empty|must not be empty"):
            synthesize_mission(req)
    
    def test_rejects_overlong_id(self):
        """ID exceeding max length raises MissionBoundaryViolation."""
        long_id = "x" * 20  # Default max is 12
        req = MissionSynthesisRequest(id=long_id, name="Valid Name")
        with pytest.raises(MissionBoundaryViolation, match="ID exceeds"):
            synthesize_mission(req)
    
    def test_rejects_empty_name(self):
        """Empty name raises MissionBoundaryViolation."""
        req = MissionSynthesisRequest(id="valid-id", name="")
        with pytest.raises(MissionBoundaryViolation, match="Name.*empty|must not be empty"):
            synthesize_mission(req)
    
    def test_rejects_overlong_name(self):
        """Name exceeding max length raises MissionBoundaryViolation."""
        long_name = "n" * 150  # Default max is 100
        req = MissionSynthesisRequest(id="valid-id", name=long_name)
        with pytest.raises(MissionBoundaryViolation, match="Name exceeds"):
            synthesize_mission(req)
    
    def test_rejects_invalid_metadata_type(self):
        """Non-string metadata value raises error."""
        # Metadata values must be strings for deterministic JSON serialization
        req = MissionSynthesisRequest(
            id="valid-id",
            name="Valid Name",
            metadata={"key": 123},  # Not a string
        )
        # B2 refinement: Union needed - synthesize_mission may raise MissionBoundaryViolation
        # from metadata validation, TypeError from canonicalization, or ValueError from
        # internal validation depending on the code path taken.
        with pytest.raises((MissionBoundaryViolation, TypeError, ValueError)):
            synthesize_mission(req)
    
    def test_rejects_too_many_tags(self):
        """Too many tags raises MissionBoundaryViolation."""
        many_tags = tuple(f"tag{i}" for i in range(30))  # Default max is 25
        req = MissionSynthesisRequest(id="valid-id", name="Valid Name", tags=many_tags)
        with pytest.raises(MissionBoundaryViolation, match="Too many tags"):
            synthesize_mission(req)


# =============================================================================
# Cycle 5: validate_mission_definition_v0_2() Entrypoint
# =============================================================================

class TestCycle5ValidateEntrypoint:
    """Cycle 5: explicit entrypoint works."""
    
    def test_validate_accepts_valid_definition(self):
        mid = MissionId(value="val-test")
        defn = MissionDefinition(id=mid, name="Valid Mission")
        
        assert validate_mission_definition_v0_2(defn) is None
    
    def test_validate_rejects_invalid_definition(self):
        mid = MissionId(value="")  # Empty ID
        defn = MissionDefinition(id=mid, name="Test")
        
        with pytest.raises(MissionBoundaryViolation):
            validate_mission_definition_v0_2(defn)
    
    def test_validate_accepts_custom_config(self):
        config = MissionBoundaryConfig(max_name_chars=5)
        mid = MissionId(value="test")
        defn = MissionDefinition(id=mid, name="TooLong")
        
        with pytest.raises(MissionBoundaryViolation, match="Name exceeds"):
            validate_mission_definition_v0_2(defn, config)


# =============================================================================
# Cycle 6: Error Taxonomy
# =============================================================================

class TestCycle6ErrorTaxonomy:
    """Cycle 6: Error messages are stable and typed."""
    
    def test_error_messages_are_stable(self):
        """Same invalid input produces same error message."""
        req = MissionSynthesisRequest(id="", name="Test")
        
        try:
            synthesize_mission(req)
            pytest.fail("Should have raised")
        except MissionBoundaryViolation as e1:
            msg1 = str(e1)
        
        try:
            synthesize_mission(req)
            pytest.fail("Should have raised")
        except MissionBoundaryViolation as e2:
            msg2 = str(e2)
        
        assert msg1 == msg2
    
    def test_all_validation_errors_are_boundary_violations(self):
        """All validation failures raise MissionBoundaryViolation."""
        invalid_cases = [
            MissionSynthesisRequest(id="", name="Test"),  # Empty ID
            MissionSynthesisRequest(id="valid", name=""),  # Empty name
            MissionSynthesisRequest(id="x" * 20, name="Test"),  # Long ID
        ]
        
        for req in invalid_cases:
            with pytest.raises(MissionBoundaryViolation):
                synthesize_mission(req)


# =============================================================================
# Cycle 7: Golden Fixture Determinism Proof
# =============================================================================

class TestCycle7GoldenFixture:
    """Cycle 7: Golden fixture produces expected deterministic output."""
    
    def test_golden_fixture_synthesis(self):
        """Golden fixture synthesizes correctly."""
        req = MissionSynthesisRequest(**GOLDEN_REQUEST)
        result = synthesize_mission(req)
        
        assert result.id.value == GOLDEN_REQUEST["id"]
        assert result.name == GOLDEN_REQUEST["name"]
        assert result.description == GOLDEN_REQUEST["description"]
        assert result.tags == GOLDEN_REQUEST["tags"]
    
    def test_golden_fixture_hash_stability(self):
        """Golden fixture produces stable hash across runs."""
        req = MissionSynthesisRequest(**GOLDEN_REQUEST)
        result = synthesize_mission(req)
        state = MissionRegistryState(missions=(result,))
        
        hash1 = state_hash(state)
        
        # Synthesize again
        result2 = synthesize_mission(req)
        state2 = MissionRegistryState(missions=(result2,))
        hash2 = state_hash(state2)
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex
        
        # Print for DETERMINISM_PROOF.txt capture
        print(f"\nGOLDEN_HASH = \"{hash1}\"")


# =============================================================================
# Cycle 8: Post-Review Contract Decisions
# =============================================================================

class TestCycle8ContractDecisions:
    """Cycle 8: Explicit tests for contract decisions."""
    
    def test_decision_tags_are_order_significant(self):
        """Contract: Different tag order produces different MissionDefinition."""
        req1 = MissionSynthesisRequest(id="t1", name="T", tags=("a", "b"))
        req2 = MissionSynthesisRequest(id="t1", name="T", tags=("b", "a"))
        
        res1 = synthesize_mission(req1)
        res2 = synthesize_mission(req2)
        
        # Definitions must differ
        assert res1 != res2
        assert res1.tags == ("a", "b")
        assert res2.tags == ("b", "a")
        
        # Hashes must differ
        state1 = MissionRegistryState(missions=(res1,))
        state2 = MissionRegistryState(missions=(res2,))
        assert state_hash(state1) != state_hash(state2)

    def test_decision_whitespace_is_rejected_without_stripping(self):
        """Contract: Whitespace-only rejected; non-empty whitespace PRESERVED."""
        # 1. Whitespace-only rejected (already covered in Cycle 4, but explicit here)
        with pytest.raises(MissionBoundaryViolation):
            synthesize_mission(MissionSynthesisRequest(id="   ", name="Test"))
            
        # 2. Leading/trailing whitespace preserved (NOT stripped)
        # This matches existing MissionId behavior
        req = MissionSynthesisRequest(id="  val-id  ", name="  Test Name  ")
        res = synthesize_mission(req)
        
        assert res.id.value == "  val-id  "
        assert res.name == "  Test Name  "


# =============================================================================
# Cycle 9: Hygiene & Hardening Proofs
# =============================================================================

class TestCycle9Hygiene:
    """Cycle 9: Proof of ID whitespace contract and content rules."""
    
    def test_proof_id_whitespace_only_is_rejected(self):
        """P0: Whitespace-only ID MUST be rejected by authoritative validator."""
        # This confirms validate_mission_id behavior is active
        with pytest.raises(MissionBoundaryViolation, match="Mission ID.*empty|must not be empty"):
            synthesize_mission(MissionSynthesisRequest(id="   ", name="Test"))
            
    def test_proof_tags_cannot_be_empty_or_whitespace(self):
        """P1: Tags must not be empty or whitespace-only."""
        req = MissionSynthesisRequest(
            id="tag-test", 
            name="Tag Test",
            tags=("valid", "   "),  # Invalid tag
        )
        # This will fail until boundaries.py is updated
        with pytest.raises(MissionBoundaryViolation, match="Tag.*empty"):
            synthesize_mission(req)

    def test_proof_metadata_keys_cannot_be_empty_or_whitespace(self):
        """P1: Metadata keys must not be empty or whitespace-only."""
        req = MissionSynthesisRequest(
            id="meta-test", 
            name="Meta Test",
            metadata={"   ": "value"},  # Invalid key
        )
        # This will fail until boundaries.py is updated
        with pytest.raises(MissionBoundaryViolation, match="Metadata.*key.*empty"):
            synthesize_mission(req)

