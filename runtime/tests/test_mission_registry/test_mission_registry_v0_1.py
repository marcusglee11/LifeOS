"""
Mission Registry v0.1 — Spec Conformance Tests

TDD test suite covering:
- Public API imports
- Schema conformance
- Canonical JSON determinism
- Hash stability
- Validation boundaries
- Immutability guarantees
- Version constant
- Metadata canonical ordering
- Tag order policy
"""
import json
import pytest

from runtime.mission import (
    MissionId,
    MissionDefinition,
    MissionRegistryState,
    MissionRegistry,
    MissionBoundaryViolation,
    MissionNotFoundError,
    MissionConflictError,
    MissionBoundaryConfig,
    validate_mission_id,
    validate_mission_definition,
    canonical_json,
    state_hash,
    __version__,
)


# =============================================================================
# Cycle 1: Public API
# =============================================================================

class TestCycle1PublicAPI:
    """Cycle 1: Module exists and exports public API."""
    
    def test_public_api_imports(self):
        """All public symbols must be importable from runtime.mission."""
        # Data types
        assert MissionId is not None
        assert MissionDefinition is not None
        assert MissionRegistryState is not None
        
        # Registry
        assert MissionRegistry is not None
        
        # Exceptions
        assert MissionBoundaryViolation is not None
        assert MissionNotFoundError is not None
        assert MissionConflictError is not None
        
        # Configuration
        assert MissionBoundaryConfig is not None
        
        # Functions
        assert validate_mission_id is not None
        assert validate_mission_definition is not None
        assert canonical_json is not None
        assert state_hash is not None
    
    def test_version_exists_and_is_semver(self):
        """Version constant exists and follows semver pattern."""
        assert __version__ is not None
        assert isinstance(__version__, str)
        parts = __version__.split(".")
        assert len(parts) == 3, "Version should be X.Y.Z"
        for part in parts:
            assert part.isdigit(), f"Version part '{part}' should be numeric"
            
    def test_version_constant_is_exported(self):
        """TIER3_MISSION_REGISTRY_VERSION is exported."""
        from runtime.mission import TIER3_MISSION_REGISTRY_VERSION
        assert TIER3_MISSION_REGISTRY_VERSION == __version__


# =============================================================================
# Cycle 2: Schema Conformance
# =============================================================================

class TestCycle2SchemaConformance:
    """Cycle 2: Data type schema is exact."""
    
    def test_mission_id_structure(self):
        """MissionId has value attribute."""
        mid = MissionId(value="test-id")
        assert mid.value == "test-id"
    
    def test_mission_definition_structure(self):
        """MissionDefinition has all required fields."""
        mid = MissionId(value="test-id")
        defn = MissionDefinition(
            id=mid,
            name="Test Mission",
            description="A test",
            tags=("tag1", "tag2"),
            metadata=(("key1", "val1"),),
        )
        assert defn.id == mid
        assert defn.name == "Test Mission"
        assert defn.description == "A test"
        assert defn.tags == ("tag1", "tag2")
        assert defn.metadata == (("key1", "val1"),)
    
    def test_mission_definition_defaults(self):
        """MissionDefinition has sensible defaults."""
        mid = MissionId(value="test-id")
        defn = MissionDefinition(id=mid, name="Test Mission")
        assert defn.description == ""
        assert defn.tags == ()
        assert defn.metadata == ()
    
    def test_mission_registry_state_structure(self):
        """MissionRegistryState has missions and version."""
        state = MissionRegistryState(missions=())
        assert state.missions == ()
        assert state.version == __version__


# =============================================================================
# Cycle 3: Canonical JSON
# =============================================================================

class TestCycle3CanonicalJSON:
    """Cycle 3: Canonical JSON is deterministic."""
    
    def test_canonical_json_is_stable(self):
        """Same state produces identical canonical JSON on repeated calls."""
        mid = MissionId(value="test-id")
        defn = MissionDefinition(id=mid, name="Test Mission")
        state = MissionRegistryState(missions=(defn,))
        
        json1 = canonical_json(state)
        json2 = canonical_json(state)
        
        assert json1 == json2
    
    def test_canonical_json_settings_are_pinned(self):
        """Canonical JSON uses pinned settings."""
        mid = MissionId(value="test-id")
        defn = MissionDefinition(
            id=mid,
            name="Test_Unicode_日本語",  # Non-ASCII, no spaces to confuse separator check
        )
        state = MissionRegistryState(missions=(defn,))
        
        result = canonical_json(state)
        
        # Should NOT escape unicode (ensure_ascii=False)
        assert "日本語" in result
        # Should have no spaces (separators)
        assert ": " not in result
        assert ", " not in result
    
    def test_canonical_json_roundtrip(self):
        """json.loads(canonical_json(state)) matches state.to_dict()."""
        mid = MissionId(value="test-id")
        defn = MissionDefinition(id=mid, name="Test Mission", tags=("a", "b"))
        state = MissionRegistryState(missions=(defn,))
        
        parsed = json.loads(canonical_json(state))
        
        assert parsed == state.to_dict()


# =============================================================================
# Cycle 4: Hash Stability
# =============================================================================

class TestCycle4HashStability:
    """Cycle 4: State hash is stable."""
    
    def test_state_hash_is_stable(self):
        """Same state produces identical hash on repeated calls."""
        mid = MissionId(value="test-id")
        defn = MissionDefinition(id=mid, name="Test Mission")
        state = MissionRegistryState(missions=(defn,))
        
        hash1 = state_hash(state)
        hash2 = state_hash(state)
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex
    
    def test_different_states_different_hashes(self):
        """Different states produce different hashes."""
        mid1 = MissionId(value="id-1")
        mid2 = MissionId(value="id-2")
        defn1 = MissionDefinition(id=mid1, name="Mission 1")
        defn2 = MissionDefinition(id=mid2, name="Mission 2")
        
        state1 = MissionRegistryState(missions=(defn1,))
        state2 = MissionRegistryState(missions=(defn2,))
        
        assert state_hash(state1) != state_hash(state2)


# =============================================================================
# Cycle 5: Validation Boundaries
# =============================================================================

class TestCycle5ValidationBoundaries:
    """Cycle 5: Validation boundaries are enforced."""
    
    def test_validate_mission_id_rejects_empty(self):
        """Empty mission ID raises MissionBoundaryViolation."""
        mid = MissionId(value="")
        with pytest.raises(MissionBoundaryViolation, match="must not be empty"):
            validate_mission_id(mid)
    
    def test_validate_mission_id_rejects_whitespace_only(self):
        """Whitespace-only mission ID raises MissionBoundaryViolation."""
        mid = MissionId(value="   ")
        with pytest.raises(MissionBoundaryViolation, match="must not be empty"):
            validate_mission_id(mid)
    
    def test_validate_definition_rejects_empty_name(self):
        """Empty name raises MissionBoundaryViolation."""
        mid = MissionId(value="valid-id")
        defn = MissionDefinition(id=mid, name="")
        with pytest.raises(MissionBoundaryViolation, match="Name must not be empty"):
            validate_mission_definition(defn)
    
    def test_validate_definition_rejects_overlong_name(self):
        """Overlong name raises MissionBoundaryViolation."""
        config = MissionBoundaryConfig(max_name_chars=10)
        mid = MissionId(value="valid-id")
        defn = MissionDefinition(id=mid, name="x" * 11)
        with pytest.raises(MissionBoundaryViolation, match="Name exceeds"):
            validate_mission_definition(defn, config)
    
    def test_validate_definition_rejects_overlong_description(self):
        """Overlong description raises MissionBoundaryViolation."""
        config = MissionBoundaryConfig(max_description_chars=10)
        mid = MissionId(value="valid-id")
        defn = MissionDefinition(id=mid, name="Valid", description="x" * 11)
        with pytest.raises(MissionBoundaryViolation, match="Description exceeds"):
            validate_mission_definition(defn, config)
    
    def test_validate_definition_rejects_too_many_tags(self):
        """Too many tags raises MissionBoundaryViolation."""
        config = MissionBoundaryConfig(max_tags=2)
        mid = MissionId(value="valid-id")
        defn = MissionDefinition(id=mid, name="Valid", tags=("a", "b", "c"))
        with pytest.raises(MissionBoundaryViolation, match="Too many tags"):
            validate_mission_definition(defn, config)
    
    def test_validate_definition_rejects_overlong_tag(self):
        """Overlong tag raises MissionBoundaryViolation."""
        config = MissionBoundaryConfig(max_tag_chars=5)
        mid = MissionId(value="valid-id")
        defn = MissionDefinition(id=mid, name="Valid", tags=("toolong",))
        with pytest.raises(MissionBoundaryViolation, match="Tag\\[0\\] exceeds"):
            validate_mission_definition(defn, config)


# =============================================================================
# Cycle 6: Immutability
# =============================================================================

class TestCycle6Immutability:
    """Cycle 6: Data types are immutable."""
    
    def test_mission_id_is_frozen(self):
        """MissionId is frozen (immutable)."""
        mid = MissionId(value="test")
        with pytest.raises(Exception):  # FrozenInstanceError
            mid.value = "changed"
    
    def test_mission_definition_is_frozen(self):
        """MissionDefinition is frozen (immutable)."""
        mid = MissionId(value="test")
        defn = MissionDefinition(id=mid, name="Test")
        with pytest.raises(Exception):  # FrozenInstanceError
            defn.name = "changed"
    
    def test_registry_operations_return_new_instances(self):
        """Registry operations return new instances, not mutations."""
        mid = MissionId(value="test")
        defn = MissionDefinition(id=mid, name="Test")
        
        reg1 = MissionRegistry()
        reg2 = reg1.register(defn)
        
        assert reg1 is not reg2
        assert len(reg1) == 0
        assert len(reg2) == 1


# =============================================================================
# Cycle 7: Metadata Canonical Ordering
# =============================================================================

class TestCycle7MetadataCanonicalOrdering:
    """Cycle 7: Metadata is canonically ordered in output."""
    
    def test_metadata_permutations_produce_same_canonical_json(self):
        """Different metadata insertion orders produce same canonical JSON."""
        mid = MissionId(value="test")
        
        # Same metadata, different order
        defn1 = MissionDefinition(
            id=mid,
            name="Test",
            metadata=(("zebra", "z"), ("alpha", "a"), ("middle", "m")),
        )
        defn2 = MissionDefinition(
            id=mid,
            name="Test",
            metadata=(("alpha", "a"), ("middle", "m"), ("zebra", "z")),
        )
        
        state1 = MissionRegistryState(missions=(defn1,))
        state2 = MissionRegistryState(missions=(defn2,))
        
        # Should produce identical canonical JSON (metadata sorted by key)
        assert canonical_json(state1) == canonical_json(state2)
        assert state_hash(state1) == state_hash(state2)


# =============================================================================
# Cycle 8: Tag Order Policy
# =============================================================================

class TestCycle8TagOrderPolicy:
    """Cycle 8: Tags are order-significant (explicit policy)."""
    
    def test_different_tag_orders_produce_different_hashes(self):
        """Different tag orders produce different hashes (order-significant)."""
        mid = MissionId(value="test")
        
        defn1 = MissionDefinition(id=mid, name="Test", tags=("a", "b", "c"))
        defn2 = MissionDefinition(id=mid, name="Test", tags=("c", "b", "a"))
        
        state1 = MissionRegistryState(missions=(defn1,))
        state2 = MissionRegistryState(missions=(defn2,))
        
        # Should produce DIFFERENT hashes (order-significant policy)
        assert state_hash(state1) != state_hash(state2)
    
    def test_same_tag_order_produces_same_hash(self):
        """Same tag order produces same hash."""
        mid = MissionId(value="test")
        
        defn1 = MissionDefinition(id=mid, name="Test", tags=("a", "b"))
        defn2 = MissionDefinition(id=mid, name="Test", tags=("a", "b"))
        
        state1 = MissionRegistryState(missions=(defn1,))
        state2 = MissionRegistryState(missions=(defn2,))
        
        assert state_hash(state1) == state_hash(state2)


# =============================================================================
# Cycle 9: Registry Operations (Validation & Semantics)
# =============================================================================

class TestCycle9RegistryOperations:
    """Cycle 9: Registry enforces boundaries and operational contracts."""
    
    def test_registry_enforces_id_length_boundary_on_register(self):
        """A1: Registry enforces boundaries (e.g. ID length) on register."""
        registry = MissionRegistry()
        long_id = "X" * 20  # Max is 12
        # Note: MissionDefinition.create does NOT validate, only Registry does.
        m_bad = MissionDefinition.create(id=long_id, name="Test", goal="Goal")
        
        with pytest.raises(MissionBoundaryViolation, match="Mission ID exceeds"):
            registry.register(m_bad)

    def test_registry_enforces_boundaries_on_update(self):
        """A3: Registry enforces boundaries on update."""
        registry = MissionRegistry()
        m_ok = MissionDefinition.create(id="M1", name="OK", goal="OK")
        registry.register(m_ok)
        
        long_name = "N" * 150 # Max 100
        m_bad = MissionDefinition.create(id="M1", name=long_name, goal="OK")
        
        # Note: boundaries.py raises "Name exceeds..."
        with pytest.raises(MissionBoundaryViolation, match="Name exceeds"):
            registry.update(m_bad)

    def test_remove_raises_on_missing_id(self):
        """B1: remove() raises MissionNotFoundError if ID missing."""
        registry = MissionRegistry()
        with pytest.raises(MissionNotFoundError):
            registry.remove(MissionId("MISSING"))

    def test_metadata_serialization_check(self):
        """B2: Non-JSON-serializable metadata rejected at creation/factory time."""
        mid = MissionId("M1")
        bad_meta = {"unserializable": set([1, 2])} # Sets are not JSON serializable
        
        with pytest.raises(ValueError, match="JSON serializable"):
            MissionDefinition.create(id=mid, name="Test", goal="...", metadata=bad_meta)


# =============================================================================
# Cycle 10: Chair Conditions (Strict Boundaries)
# =============================================================================

class TestCycle10ChairConditions:
    """Cycle 10: Explicit verification of Chair-mandated P2 major conditions."""
    
    def test_registry_enforces_capacity_limit(self):
        """P2_MAJOR: Registering max_missions + 1 throws exception."""
        # Use small config for testing
        config = MissionBoundaryConfig(max_missions=2)
        registry = MissionRegistry(_config=config)
        
        m1 = MissionDefinition.create(id="M1", name="1", goal="1")
        m2 = MissionDefinition.create(id="M2", name="2", goal="2")
        m3 = MissionDefinition.create(id="M3", name="3", goal="3")
        
        registry = registry.register(m1).register(m2)
        
        with pytest.raises(MissionBoundaryViolation, match="registry at capacity"):
            registry.register(m3)

    def test_metadata_enforces_size_limits(self):
        """P2_MAJOR: Metadata key/value size limits enforced deterministically."""
        config = MissionBoundaryConfig(
            max_metadata_key_chars=5,
            max_metadata_value_chars=10
        )
        # Note: MissionDefinition.create validates JSON serializability,
        # but boundaries checks LENGTH during registry operations (or direct validation).
        # We test via validate_mission_definition directly or via registry.
        
        # Case 1: Key too long
        long_key = "k" * 6
        m_long_key = MissionDefinition.create(
            id="M1", name="T", goal="G", 
            metadata={long_key: "val"}
        )
        with pytest.raises(MissionBoundaryViolation, match="Metadata.*key exceeds"):
            validate_mission_definition(m_long_key, config)

        # Case 2: Value too long
        long_val = "v" * 11
        m_long_val = MissionDefinition.create(
            id="M2", name="T", goal="G", 
            metadata={"key": long_val}
        )
        with pytest.raises(MissionBoundaryViolation, match="Metadata.*value exceeds"):
            validate_mission_definition(m_long_val, config)

        # Case 3: Too many pairs
        config_pairs = MissionBoundaryConfig(max_metadata_pairs=2)
        m_many_pairs = MissionDefinition.create(
            id="M3", name="T", goal="G", 
            metadata={"k1": "v1", "k2": "v2", "k3": "v3"}
        )
        # Note: create sorts keys, returns tuple of 3 items
        with pytest.raises(MissionBoundaryViolation, match="Too many metadata pairs"):
            validate_mission_definition(m_many_pairs, config_pairs)


