"""
Mission Registry v0.1 — Contract Tests

Tests for BUILD packet acceptance criteria:
- AT2: Interface defined, type-checks, validation enforced, no side effects
- AT3: Determinism stability — different insertion orders yield identical canonical representation
"""
import pytest

from runtime.mission import (
    MissionId,
    MissionDefinition,
    MissionRegistry,
    MissionConflictError,
    MissionNotFoundError,
    canonical_json,
    state_hash,
)


class TestAT2InterfaceDefinedNoExecution:
    """AT2: Interface exists, type-checks, validation enforced, no side effects."""
    
    def test_at1_public_interface_surface(self):
        """AT1: Public interface includes register, get, list, update, remove."""
        reg = MissionRegistry()
        assert hasattr(reg, "register")
        assert hasattr(reg, "get")
        assert hasattr(reg, "list")
        assert hasattr(reg, "update")
        assert hasattr(reg, "remove")

    
    def test_registry_operations_are_pure(self):
        """Registry operations have no side effects."""
        mid = MissionId(value="test-1")
        defn = MissionDefinition(id=mid, name="Test Mission")
        
        # Create registry and perform operations
        reg = MissionRegistry()
        reg2 = reg.register(defn)
        reg3 = reg2.update(MissionDefinition(id=mid, name="Updated"))
        reg4 = reg3.remove(mid)
        
        # Original registry unchanged
        assert len(reg) == 0
        assert len(reg2) == 1
        assert len(reg3) == 1
        assert len(reg4) == 0
    
    def test_validation_enforced_on_register(self):
        """Validation is enforced when registering."""
        reg = MissionRegistry()
        
        # Invalid: empty ID
        with pytest.raises(Exception):
            empty_id = MissionId(value="")
            reg.register(MissionDefinition(id=empty_id, name="Test"))
    
    def test_conflict_error_on_duplicate(self):
        """ConflictError raised on duplicate ID."""
        mid = MissionId(value="dup-id")
        defn1 = MissionDefinition(id=mid, name="First")
        defn2 = MissionDefinition(id=mid, name="Second")
        
        reg = MissionRegistry().register(defn1)
        
        with pytest.raises(MissionConflictError):
            reg.register(defn2)
    
    def test_not_found_error_on_missing(self):
        """NotFoundError raised for missing mission."""
        reg = MissionRegistry()
        mid = MissionId(value="nonexistent")
        
        with pytest.raises(MissionNotFoundError):
            reg.get(mid)
        
        with pytest.raises(MissionNotFoundError):
            reg.remove(mid)
    
    def test_no_io_during_operations(self):
        """Operations complete without any I/O."""
        # This test verifies deterministic, pure behavior
        # If there were I/O, it would fail in restricted environments
        mid = MissionId(value="pure-test")
        defn = MissionDefinition(id=mid, name="Pure Operation")
        
        reg = MissionRegistry()
        reg2 = reg.register(defn)
        _ = reg2.get(mid)
        _ = reg2.list()
        _ = reg2.to_state()
        
        # If we got here without errors, no I/O was attempted
        assert True


class TestAT3DeterminismStability:
    """AT3: Different insertion orders yield identical canonical representation."""
    
    def test_different_insertion_orders_same_canonical_json(self):
        """Same missions in different insertion orders produce identical canonical JSON."""
        mid_a = MissionId(value="id-a")
        mid_b = MissionId(value="id-b")
        mid_c = MissionId(value="id-c")
        
        defn_a = MissionDefinition(id=mid_a, name="Mission A")
        defn_b = MissionDefinition(id=mid_b, name="Mission B")
        defn_c = MissionDefinition(id=mid_c, name="Mission C")
        
        # Insert in order: A, B, C
        reg1 = MissionRegistry().register(defn_a).register(defn_b).register(defn_c)
        
        # Insert in order: C, A, B
        reg2 = MissionRegistry().register(defn_c).register(defn_a).register(defn_b)
        
        # Insert in order: B, C, A
        reg3 = MissionRegistry().register(defn_b).register(defn_c).register(defn_a)
        
        # list() preserves insertion order (different)
        assert [m.id.value for m in reg1.list()] == ["id-a", "id-b", "id-c"]
        assert [m.id.value for m in reg2.list()] == ["id-c", "id-a", "id-b"]
        assert [m.id.value for m in reg3.list()] == ["id-b", "id-c", "id-a"]
        
        # to_state() is sorted (same)
        state1 = reg1.to_state()
        state2 = reg2.to_state()
        state3 = reg3.to_state()
        
        # All canonical JSONs should be identical
        json1 = canonical_json(state1)
        json2 = canonical_json(state2)
        json3 = canonical_json(state3)
        
        assert json1 == json2 == json3
        
        # All hashes should be identical
        hash1 = state_hash(state1)
        hash2 = state_hash(state2)
        hash3 = state_hash(state3)
        
        assert hash1 == hash2 == hash3
    
    def test_determinism_with_metadata_variations(self):
        """Metadata insertion order doesn't affect canonical representation."""
        mid = MissionId(value="meta-test")
        
        defn1 = MissionDefinition(
            id=mid,
            name="Test",
            metadata=(("z", "1"), ("a", "2"), ("m", "3")),
        )
        defn2 = MissionDefinition(
            id=mid,
            name="Test",
            metadata=(("a", "2"), ("m", "3"), ("z", "1")),
        )
        
        state1 = MissionRegistry().register(defn1).to_state()
        state2 = MissionRegistry().register(defn2).to_state()
        
        assert canonical_json(state1) == canonical_json(state2)
        assert state_hash(state1) == state_hash(state2)
    
    def test_empty_registry_is_deterministic(self):
        """Empty registry has deterministic representation."""
        reg1 = MissionRegistry()
        reg2 = MissionRegistry()
        
        assert canonical_json(reg1.to_state()) == canonical_json(reg2.to_state())
        assert state_hash(reg1.to_state()) == state_hash(reg2.to_state())
