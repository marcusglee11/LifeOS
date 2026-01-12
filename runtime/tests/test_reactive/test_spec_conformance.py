"""
Reactive Task Layer v0.1 — Spec Conformance Tests

TDD test suite with 35 tests covering:
- Public API imports (1)
- Schema conformance (4)
- Canonical JSON (3)
- Hash stability (1)
- Validation boundaries (8)
- Immutability (1)
- Version constant (3)
- Determinism hardening (2)
- Validation edge cases (4)
- Unicode coverage (3)
- Build plan surface (5)
"""
import json
import pytest


class TestCycle1PublicAPI:
    """Cycle 1: Module exists and exports public API."""

    def test_public_api_imports(self):
        """All public symbols must be importable from runtime.reactive."""
        from runtime.reactive import (
            ReactiveTask,
            ReactiveTaskRequest,
            REACTIVE_LAYER_VERSION,
            build_plan_surface,
            to_plan_surface,
            canonical_json,
            surface_hash,
            validate_request,
            validate_surface,
            ReactiveBoundaryConfig,
            ReactiveBoundaryViolation,
        )
        # All imports succeeded - verify they are not None
        assert ReactiveTask is not None
        assert ReactiveTaskRequest is not None
        assert REACTIVE_LAYER_VERSION is not None
        assert build_plan_surface is not None
        assert to_plan_surface is not None
        assert canonical_json is not None
        assert surface_hash is not None
        assert validate_request is not None
        assert validate_surface is not None
        assert ReactiveBoundaryConfig is not None
        assert ReactiveBoundaryViolation is not None


class TestCycle2SchemaConformance:
    """Cycle 2: Plan surface schema is exact."""

    def test_plan_surface_schema_exact(self):
        """Surface has exactly the required keys, no more, no less."""
        from runtime.reactive import ReactiveTaskRequest, to_plan_surface
        
        req = ReactiveTaskRequest(id="t1", title="Test", description="Desc", tags=("a",))
        surface = to_plan_surface(req)
        
        # Top-level keys (set equality)
        assert set(surface.keys()) == {"version", "task", "constraints"}
        # Task keys
        assert set(surface["task"].keys()) == {"id", "title", "description", "tags"}
        # Constraints keys
        assert set(surface["constraints"].keys()) == {"max_payload_chars"}
        # Version literal
        assert surface["version"] == "reactive_task_layer.v0.1"

    def test_constraints_default_matches_config(self):
        """max_payload_chars in surface equals config default."""
        from runtime.reactive import ReactiveTaskRequest, to_plan_surface, ReactiveBoundaryConfig
        
        req = ReactiveTaskRequest(id="t1", title="Test")
        surface = to_plan_surface(req)
        config = ReactiveBoundaryConfig()
        
        assert surface["constraints"]["max_payload_chars"] == config.max_payload_chars

    def test_tags_none_emits_empty_list(self):
        """tags=None in request produces [] in surface."""
        from runtime.reactive import ReactiveTaskRequest, to_plan_surface
        
        req = ReactiveTaskRequest(id="t1", title="Test", tags=None)
        surface = to_plan_surface(req)
        
        assert surface["task"]["tags"] == []

    def test_tags_order_preserved(self):
        """Tags order is preserved: ["b","a"] stays ["b","a"]."""
        from runtime.reactive import ReactiveTaskRequest, to_plan_surface, canonical_json
        
        req = ReactiveTaskRequest(id="t1", title="Test", tags=("b", "a"))
        surface = to_plan_surface(req)
        
        assert surface["task"]["tags"] == ["b", "a"]
        # Also check in canonical JSON
        cj = canonical_json(surface)
        assert '"tags":["b","a"]' in cj


class TestCycle3CanonicalJSON:
    """Cycle 3: Canonical JSON is deterministic."""

    def test_canonical_json_is_stable(self):
        """Same request produces identical canonical JSON on repeated calls."""
        from runtime.reactive import ReactiveTaskRequest, to_plan_surface, canonical_json
        
        req = ReactiveTaskRequest(id="t1", title="Test", description="Desc")
        surface1 = to_plan_surface(req)
        surface2 = to_plan_surface(req)
        
        cj1 = canonical_json(surface1)
        cj2 = canonical_json(surface2)
        
        assert cj1 == cj2

    def test_canonical_json_settings_are_pinned(self):
        """Canonical JSON uses ensure_ascii=True (unicode escaped)."""
        from runtime.reactive import ReactiveTaskRequest, to_plan_surface, canonical_json
        
        # Unicode character in description
        req = ReactiveTaskRequest(id="t1", title="Test", description="café")
        surface = to_plan_surface(req)
        cj = canonical_json(surface)
        
        # ensure_ascii=True means é is escaped
        assert "\\u00e9" in cj or "caf" in cj  # é -> \u00e9
        # Verify no literal é appears (ASCII only)
        assert all(ord(c) < 128 for c in cj)

    def test_canonical_json_roundtrip(self):
        """json.loads(canonical_json(surface)) == surface."""
        from runtime.reactive import ReactiveTaskRequest, to_plan_surface, canonical_json
        
        req = ReactiveTaskRequest(id="t1", title="Test", description="Desc", tags=("a", "b"))
        surface = to_plan_surface(req)
        cj = canonical_json(surface)
        
        roundtrip = json.loads(cj)
        assert roundtrip == surface


class TestCycle4HashStability:
    """Cycle 4: Surface hash is stable."""

    def test_surface_hash_is_stable(self):
        """Same request produces identical hash on repeated calls."""
        from runtime.reactive import ReactiveTaskRequest, to_plan_surface, surface_hash, canonical_json
        import hashlib
        
        req = ReactiveTaskRequest(id="t1", title="Test", description="Desc")
        surface1 = to_plan_surface(req)
        surface2 = to_plan_surface(req)
        
        h1 = surface_hash(surface1)
        h2 = surface_hash(surface2)
        
        assert h1 == h2
        assert len(h1) == 64  # SHA256 hex
        # Verify matches manual computation
        expected = hashlib.sha256(canonical_json(surface1).encode("utf-8")).hexdigest()
        assert h1 == expected


class TestCycle5ValidationBoundaries:
    """Cycle 5: Validation boundaries are enforced."""

    def test_validate_request_accepts_valid(self):
        """Valid request passes validation."""
        from runtime.reactive import ReactiveTaskRequest, validate_request
        
        req = ReactiveTaskRequest(id="t1", title="Valid Title", description="Valid desc")
        # Should not raise
        validate_request(req)

    def test_validate_request_rejects_empty_id(self):
        """Empty id raises ReactiveBoundaryViolation."""
        from runtime.reactive import ReactiveTaskRequest, validate_request, ReactiveBoundaryViolation
        
        req = ReactiveTaskRequest(id="", title="Test", description="Desc")
        with pytest.raises(ReactiveBoundaryViolation, match="id must not be empty"):
            validate_request(req)
        
        # Also test whitespace-only id
        req2 = ReactiveTaskRequest(id="   ", title="Test", description="Desc")
        with pytest.raises(ReactiveBoundaryViolation, match="id must not be empty"):
            validate_request(req2)

    def test_validate_request_rejects_invalid_tags_type(self):
        """tags must be tuple[str, ...], not string or other types."""
        from runtime.reactive import ReactiveTaskRequest, validate_request, ReactiveBoundaryViolation
        
        # String instead of tuple (common mistake - iterates chars)
        req = ReactiveTaskRequest(id="t1", title="Test", tags="abc")  # type: ignore
        with pytest.raises(ReactiveBoundaryViolation, match="tags must be tuple"):
            validate_request(req)
        
        # Non-string element in tuple
        req2 = ReactiveTaskRequest(id="t1", title="Test", tags=("valid", 123))  # type: ignore
        with pytest.raises(ReactiveBoundaryViolation, match=r"tag\[1\] must be str"):
            validate_request(req2)

    def test_validate_request_rejects_empty_title(self):
        """Empty title raises ReactiveBoundaryViolation."""
        from runtime.reactive import ReactiveTaskRequest, validate_request, ReactiveBoundaryViolation
        
        req = ReactiveTaskRequest(id="t1", title="", description="Desc")
        with pytest.raises(ReactiveBoundaryViolation, match="title must not be empty"):
            validate_request(req)
        
        # Also test whitespace-only title
        req2 = ReactiveTaskRequest(id="t1", title="   ", description="Desc")
        with pytest.raises(ReactiveBoundaryViolation, match="title must not be empty"):
            validate_request(req2)

    def test_validate_request_rejects_overlong_description(self):
        """Description exceeding max chars raises ReactiveBoundaryViolation."""
        from runtime.reactive import ReactiveTaskRequest, validate_request, ReactiveBoundaryViolation, ReactiveBoundaryConfig
        
        config = ReactiveBoundaryConfig()
        long_desc = "x" * (config.max_description_chars + 1)
        req = ReactiveTaskRequest(id="t1", title="Test", description=long_desc)
        
        with pytest.raises(ReactiveBoundaryViolation, match="description exceeds"):
            validate_request(req, config)

    def test_validate_request_rejects_too_many_tags(self):
        """Too many tags raises ReactiveBoundaryViolation."""
        from runtime.reactive import ReactiveTaskRequest, validate_request, ReactiveBoundaryViolation, ReactiveBoundaryConfig
        
        config = ReactiveBoundaryConfig()
        too_many = tuple(f"tag{i}" for i in range(config.max_tags + 1))
        req = ReactiveTaskRequest(id="t1", title="Test", tags=too_many)
        
        with pytest.raises(ReactiveBoundaryViolation, match="too many tags"):
            validate_request(req, config)

    def test_validate_request_rejects_overlong_tag(self):
        """Tag exceeding max chars raises ReactiveBoundaryViolation."""
        from runtime.reactive import ReactiveTaskRequest, validate_request, ReactiveBoundaryViolation, ReactiveBoundaryConfig
        
        config = ReactiveBoundaryConfig()
        long_tag = "x" * (config.max_tag_chars + 1)
        req = ReactiveTaskRequest(id="t1", title="Test", tags=(long_tag,))
        
        with pytest.raises(ReactiveBoundaryViolation, match="tag\\[0\\] exceeds"):
            validate_request(req, config)

    def test_validate_surface_rejects_oversized_payload(self):
        """Surface exceeding max_payload_chars raises ReactiveBoundaryViolation."""
        from runtime.reactive import (
            ReactiveTaskRequest, to_plan_surface, validate_surface,
            ReactiveBoundaryViolation, ReactiveBoundaryConfig
        )
        
        # Create a config with very small payload limit
        tiny_config = ReactiveBoundaryConfig(max_payload_chars=10)
        req = ReactiveTaskRequest(id="t1", title="Test", description="This will be too long")
        surface = to_plan_surface(req, tiny_config)
        
        with pytest.raises(ReactiveBoundaryViolation, match="surface payload exceeds"):
            validate_surface(surface, tiny_config)


class TestCycle6Immutability:
    """Cycle 6: Dataclasses are frozen."""

    def test_dataclasses_are_frozen(self):
        """Attempting mutation raises FrozenInstanceError."""
        from runtime.reactive import ReactiveTask, ReactiveTaskRequest, ReactiveBoundaryConfig
        from dataclasses import FrozenInstanceError
        
        task = ReactiveTask(id="t1", title="Test", description="Desc")
        with pytest.raises(FrozenInstanceError):
            task.title = "New Title"
        
        req = ReactiveTaskRequest(id="t1", title="Test")
        with pytest.raises(FrozenInstanceError):
            req.title = "New Title"
        
        config = ReactiveBoundaryConfig()
        with pytest.raises(FrozenInstanceError):
            config.max_tags = 100


class TestVersionConstant:
    """A3: Version constant is authoritative and deterministic."""

    def test_version_constant_exists_and_is_string(self):
        """REACTIVE_LAYER_VERSION exists and is a string."""
        from runtime.reactive import REACTIVE_LAYER_VERSION
        
        assert REACTIVE_LAYER_VERSION is not None
        assert isinstance(REACTIVE_LAYER_VERSION, str)

    def test_version_constant_matches_semantic_pattern(self):
        """Version follows expected semantic pattern."""
        from runtime.reactive import REACTIVE_LAYER_VERSION
        import re
        
        # Expected: reactive_task_layer.vX.Y
        pattern = r"^reactive_task_layer\.v\d+\.\d+$"
        assert re.match(pattern, REACTIVE_LAYER_VERSION)

    def test_surface_uses_version_constant(self):
        """Surface version field matches the authoritative constant."""
        from runtime.reactive import ReactiveTaskRequest, to_plan_surface, REACTIVE_LAYER_VERSION
        
        req = ReactiveTaskRequest(id="t1", title="Test")
        surface = to_plan_surface(req)
        
        assert surface["version"] == REACTIVE_LAYER_VERSION


class TestDeterminismHardening:
    """B1: Construction-order invariance for determinism."""

    def test_dict_insertion_order_does_not_affect_canonical_json(self):
        """Two equivalent dicts with different insertion order produce identical canonical_json."""
        from runtime.reactive import canonical_json
        
        # Build two dicts with different insertion order
        dict1 = {"a": 1, "b": 2, "c": 3}
        dict2 = {"c": 3, "a": 1, "b": 2}
        
        cj1 = canonical_json(dict1)
        cj2 = canonical_json(dict2)
        
        assert cj1 == cj2

    def test_request_field_order_does_not_affect_surface(self):
        """ReactiveTaskRequest with same values produces identical surface."""
        from runtime.reactive import ReactiveTaskRequest, to_plan_surface, canonical_json
        
        # Python 3.7+ dicts are ordered, but canonical_json uses sort_keys=True
        req1 = ReactiveTaskRequest(id="t1", title="Test", description="Desc", tags=("a", "b"))
        req2 = ReactiveTaskRequest(title="Test", id="t1", tags=("a", "b"), description="Desc")
        
        cj1 = canonical_json(to_plan_surface(req1))
        cj2 = canonical_json(to_plan_surface(req2))
        
        assert cj1 == cj2


class TestValidationEdgeCases:
    """B2: Boundary edge tests."""

    def test_validate_request_at_exact_title_limit(self):
        """Title at exactly max_title_chars passes."""
        from runtime.reactive import ReactiveTaskRequest, validate_request, ReactiveBoundaryConfig
        
        config = ReactiveBoundaryConfig()
        exact_title = "x" * config.max_title_chars
        req = ReactiveTaskRequest(id="t1", title=exact_title)
        
        # Should not raise
        validate_request(req, config)

    def test_validate_request_at_exact_description_limit(self):
        """Description at exactly max_description_chars passes."""
        from runtime.reactive import ReactiveTaskRequest, validate_request, ReactiveBoundaryConfig
        
        config = ReactiveBoundaryConfig()
        exact_desc = "x" * config.max_description_chars
        req = ReactiveTaskRequest(id="t1", title="Test", description=exact_desc)
        
        # Should not raise
        validate_request(req, config)

    def test_validate_request_at_exact_tags_limit(self):
        """Exactly max_tags tags passes."""
        from runtime.reactive import ReactiveTaskRequest, validate_request, ReactiveBoundaryConfig
        
        config = ReactiveBoundaryConfig()
        exact_tags = tuple(f"t{i}" for i in range(config.max_tags))
        req = ReactiveTaskRequest(id="t1", title="Test", tags=exact_tags)
        
        # Should not raise
        validate_request(req, config)

    def test_validate_request_at_exact_tag_char_limit(self):
        """Tag at exactly max_tag_chars passes."""
        from runtime.reactive import ReactiveTaskRequest, validate_request, ReactiveBoundaryConfig
        
        config = ReactiveBoundaryConfig()
        exact_tag = "x" * config.max_tag_chars
        req = ReactiveTaskRequest(id="t1", title="Test", tags=(exact_tag,))
        
        # Should not raise
        validate_request(req, config)


class TestUnicodeCoverage:
    """B3: Unicode handling in canonicalization."""

    def test_unicode_in_title_is_escaped(self):
        """Unicode in title is escaped via ensure_ascii=True."""
        from runtime.reactive import ReactiveTaskRequest, to_plan_surface, canonical_json
        
        req = ReactiveTaskRequest(id="t1", title="Tâche prioritaire", description="Desc")
        surface = to_plan_surface(req)
        cj = canonical_json(surface)
        
        # All characters must be ASCII
        assert all(ord(c) < 128 for c in cj)
        # Unicode â should be escaped
        assert "\\u00e2" in cj

    def test_unicode_in_description_is_escaped(self):
        """Unicode in description is escaped."""
        from runtime.reactive import ReactiveTaskRequest, to_plan_surface, canonical_json
        
        req = ReactiveTaskRequest(id="t1", title="Test", description="日本語テスト")
        surface = to_plan_surface(req)
        cj = canonical_json(surface)
        
        # All characters must be ASCII
        assert all(ord(c) < 128 for c in cj)

    def test_unicode_in_tags_is_escaped(self):
        """Unicode in tags is escaped."""
        from runtime.reactive import ReactiveTaskRequest, to_plan_surface, canonical_json
        
        req = ReactiveTaskRequest(id="t1", title="Test", tags=("étiquette", "标签"))
        surface = to_plan_surface(req)
        cj = canonical_json(surface)
        
        # All characters must be ASCII
        assert all(ord(c) < 128 for c in cj)


class TestBuildPlanSurface:
    """Tests for the enforced safe entrypoint."""

    def test_build_plan_surface_is_importable(self):
        """build_plan_surface is exported from runtime.reactive."""
        from runtime.reactive import build_plan_surface
        assert build_plan_surface is not None

    def test_build_plan_surface_produces_valid_surface(self):
        """build_plan_surface returns a valid surface for valid input."""
        from runtime.reactive import ReactiveTaskRequest, build_plan_surface, REACTIVE_LAYER_VERSION
        
        req = ReactiveTaskRequest(id="t1", title="Test", description="Desc", tags=("a", "b"))
        surface = build_plan_surface(req)
        
        assert surface["version"] == REACTIVE_LAYER_VERSION
        assert surface["task"]["id"] == "t1"
        assert surface["task"]["title"] == "Test"

    def test_build_plan_surface_rejects_invalid_request(self):
        """build_plan_surface raises on invalid request (chains validation)."""
        from runtime.reactive import ReactiveTaskRequest, build_plan_surface, ReactiveBoundaryViolation
        
        # Empty id should be rejected
        req = ReactiveTaskRequest(id="", title="Test")
        with pytest.raises(ReactiveBoundaryViolation, match="id must not be empty"):
            build_plan_surface(req)

    def test_build_plan_surface_rejects_oversized_payload(self):
        """build_plan_surface raises if surface exceeds max_payload_chars."""
        from runtime.reactive import ReactiveTaskRequest, build_plan_surface, ReactiveBoundaryConfig, ReactiveBoundaryViolation
        
        tiny_config = ReactiveBoundaryConfig(max_payload_chars=10)
        req = ReactiveTaskRequest(id="t1", title="Test", description="This will be too long")
        
        with pytest.raises(ReactiveBoundaryViolation, match="surface payload exceeds"):
            build_plan_surface(req, tiny_config)

    def test_build_plan_surface_is_deterministic(self):
        """Same input produces identical output via build_plan_surface."""
        from runtime.reactive import ReactiveTaskRequest, build_plan_surface, canonical_json, surface_hash
        
        req = ReactiveTaskRequest(id="t1", title="Test", description="Desc")
        s1 = build_plan_surface(req)
        s2 = build_plan_surface(req)
        
        assert canonical_json(s1) == canonical_json(s2)
        assert surface_hash(s1) == surface_hash(s2)
