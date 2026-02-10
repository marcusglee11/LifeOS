"""
Mission Boundary Violation Tests

Tests for mission ID and definition validation edge cases,
including boundary values, unicode, and special characters.

Per Edge Case Testing Implementation Plan - Phase 1.3
"""
import pytest
from runtime.mission.interfaces import MissionId, MissionDefinition
from runtime.mission.boundaries import (
    validate_mission_id,
    validate_mission_definition,
    MissionBoundaryConfig,
    MissionBoundaryViolation,
)


class TestMissionIdBoundaries:
    """Tests for mission ID boundary violations."""

    def test_empty_mission_id(self):
        """Empty mission ID triggers MissionBoundaryViolation."""
        mid = MissionId(value="")
        with pytest.raises(MissionBoundaryViolation) as exc_info:
            validate_mission_id(mid)

        assert "empty" in str(exc_info.value).lower()

    def test_whitespace_only_mission_id(self):
        """Whitespace-only mission ID triggers MissionBoundaryViolation."""
        mid = MissionId(value="   ")
        with pytest.raises(MissionBoundaryViolation) as exc_info:
            validate_mission_id(mid)

        assert "empty" in str(exc_info.value).lower()

    def test_mission_id_exact_boundary(self):
        """Mission ID at exact max_id_chars boundary is allowed."""
        config = MissionBoundaryConfig(max_id_chars=12)
        mid = MissionId(value="x" * 12)  # Exactly 12 chars
        validate_mission_id(mid, config)  # Should not raise

    def test_mission_id_exceeds_boundary(self):
        """Mission ID exceeding max_id_chars triggers MissionBoundaryViolation."""
        config = MissionBoundaryConfig(max_id_chars=12)
        mid = MissionId(value="x" * 13)  # 13 chars
        with pytest.raises(MissionBoundaryViolation) as exc_info:
            validate_mission_id(mid, config)

        assert "max length" in str(exc_info.value).lower()


class TestMissionNameBoundaries:
    """Tests for mission name boundary violations."""

    def test_empty_mission_name(self):
        """Empty mission name triggers MissionBoundaryViolation."""
        defn = MissionDefinition(
            id=MissionId(value="M001"),
            name="",
            description="Test"
        )
        with pytest.raises(MissionBoundaryViolation) as exc_info:
            validate_mission_definition(defn)

        assert "name" in str(exc_info.value).lower() and "empty" in str(exc_info.value).lower()

    def test_whitespace_only_mission_name(self):
        """Whitespace-only mission name triggers MissionBoundaryViolation."""
        defn = MissionDefinition(
            id=MissionId(value="M001"),
            name="   ",
            description="Test"
        )
        with pytest.raises(MissionBoundaryViolation) as exc_info:
            validate_mission_definition(defn)

        assert "name" in str(exc_info.value).lower() and "empty" in str(exc_info.value).lower()

    def test_mission_name_exact_boundary(self):
        """Mission name at exact max_name_chars boundary is allowed."""
        config = MissionBoundaryConfig(max_name_chars=100)
        defn = MissionDefinition(
            id=MissionId(value="M001"),
            name="x" * 100,  # Exactly 100 chars
            description="Test"
        )
        validate_mission_definition(defn, config)  # Should not raise

    def test_mission_name_exceeds_boundary(self):
        """Mission name exceeding max_name_chars triggers MissionBoundaryViolation."""
        config = MissionBoundaryConfig(max_name_chars=100)
        defn = MissionDefinition(
            id=MissionId(value="M001"),
            name="x" * 101,  # 101 chars
            description="Test"
        )
        with pytest.raises(MissionBoundaryViolation) as exc_info:
            validate_mission_definition(defn, config)

        assert "exceeds" in str(exc_info.value).lower() and "100" in str(exc_info.value)


class TestMissionDescriptionBoundaries:
    """Tests for mission description boundary violations."""

    def test_mission_description_exact_boundary(self):
        """Mission description at exact max_description_chars boundary is allowed."""
        config = MissionBoundaryConfig(max_description_chars=4000)
        defn = MissionDefinition(
            id=MissionId(value="M001"),
            name="Test",
            description="x" * 4000  # Exactly 4000 chars
        )
        validate_mission_definition(defn, config)  # Should not raise

    def test_mission_description_exceeds_boundary(self):
        """Mission description exceeding max_description_chars triggers MissionBoundaryViolation."""
        config = MissionBoundaryConfig(max_description_chars=4000)
        defn = MissionDefinition(
            id=MissionId(value="M001"),
            name="Test",
            description="x" * 4001  # 4001 chars
        )
        with pytest.raises(MissionBoundaryViolation) as exc_info:
            validate_mission_definition(defn, config)

        assert "exceeds" in str(exc_info.value).lower() and "4000" in str(exc_info.value)


class TestMissionTagsBoundaries:
    """Tests for mission tags boundary violations."""

    def test_tags_exact_count_boundary(self):
        """Exactly 25 tags (max_tags) is allowed."""
        config = MissionBoundaryConfig(max_tags=25)
        defn = MissionDefinition(
            id=MissionId(value="M001"),
            name="Test",
            description="Test",
            tags=tuple(f"tag{i}" for i in range(25))  # Exactly 25 tags
        )
        validate_mission_definition(defn, config)  # Should not raise

    def test_tags_exceeds_count_boundary(self):
        """26 tags (max_tags + 1) triggers MissionBoundaryViolation."""
        config = MissionBoundaryConfig(max_tags=25)
        defn = MissionDefinition(
            id=MissionId(value="M001"),
            name="Test",
            description="Test",
            tags=tuple(f"tag{i}" for i in range(26))  # 26 tags
        )
        with pytest.raises(MissionBoundaryViolation) as exc_info:
            validate_mission_definition(defn, config)

        assert "too many tags" in str(exc_info.value).lower() and "26" in str(exc_info.value) and "25" in str(exc_info.value)

    def test_whitespace_only_tag(self):
        """Whitespace-only tag triggers MissionBoundaryViolation."""
        defn = MissionDefinition(
            id=MissionId(value="M001"),
            name="Test",
            description="Test",
            tags=("valid_tag", "   ")  # Second tag is whitespace-only
        )
        with pytest.raises(MissionBoundaryViolation) as exc_info:
            validate_mission_definition(defn)

        assert "tag" in str(exc_info.value).lower() and "empty" in str(exc_info.value).lower()

    def test_tag_exact_char_boundary(self):
        """Tag at exact max_tag_chars boundary is allowed."""
        config = MissionBoundaryConfig(max_tag_chars=64)
        defn = MissionDefinition(
            id=MissionId(value="M001"),
            name="Test",
            description="Test",
            tags=("x" * 64,)  # Exactly 64 chars
        )
        validate_mission_definition(defn, config)  # Should not raise

    def test_tag_exceeds_char_boundary(self):
        """Tag exceeding max_tag_chars triggers MissionBoundaryViolation."""
        config = MissionBoundaryConfig(max_tag_chars=64)
        defn = MissionDefinition(
            id=MissionId(value="M001"),
            name="Test",
            description="Test",
            tags=("x" * 65,)  # 65 chars
        )
        with pytest.raises(MissionBoundaryViolation) as exc_info:
            validate_mission_definition(defn, config)

        assert "exceeds" in str(exc_info.value).lower() and "64" in str(exc_info.value)

    def test_empty_tag(self):
        """Empty tag triggers MissionBoundaryViolation."""
        defn = MissionDefinition(
            id=MissionId(value="M001"),
            name="Test",
            description="Test",
            tags=("valid_tag", "")
        )
        with pytest.raises(MissionBoundaryViolation) as exc_info:
            validate_mission_definition(defn)

        assert "tag" in str(exc_info.value).lower() and "empty" in str(exc_info.value).lower()


class TestMissionMetadataBoundaries:
    """Tests for mission metadata boundary violations."""

    def test_metadata_exact_count_boundary(self):
        """Exactly 50 metadata pairs (max_metadata_pairs) is allowed."""
        config = MissionBoundaryConfig(max_metadata_pairs=50)
        defn = MissionDefinition(
            id=MissionId(value="M001"),
            name="Test",
            description="Test",
            metadata=tuple((f"key{i}", f"value{i}") for i in range(50))  # Exactly 50 pairs
        )
        validate_mission_definition(defn, config)  # Should not raise

    def test_metadata_exceeds_count_boundary(self):
        """51 metadata pairs (max_metadata_pairs + 1) triggers MissionBoundaryViolation."""
        config = MissionBoundaryConfig(max_metadata_pairs=50)
        defn = MissionDefinition(
            id=MissionId(value="M001"),
            name="Test",
            description="Test",
            metadata=tuple((f"key{i}", f"value{i}") for i in range(51))  # 51 pairs
        )
        with pytest.raises(MissionBoundaryViolation) as exc_info:
            validate_mission_definition(defn, config)

        assert "too many" in str(exc_info.value).lower() and "51" in str(exc_info.value) and "50" in str(exc_info.value)

    def test_empty_metadata_tuple_allowed(self):
        """Empty metadata tuple is valid canonical form."""
        defn = MissionDefinition(
            id=MissionId(value="M001"),
            name="Test",
            description="Test",
            metadata=()  # Empty tuple
        )
        validate_mission_definition(defn)  # Should not raise

    def test_metadata_key_whitespace_only(self):
        """Whitespace-only metadata key triggers MissionBoundaryViolation."""
        defn = MissionDefinition(
            id=MissionId(value="M001"),
            name="Test",
            description="Test",
            metadata=(("   ", "value"),)
        )
        with pytest.raises(MissionBoundaryViolation) as exc_info:
            validate_mission_definition(defn)

        assert "metadata" in str(exc_info.value).lower() and "empty" in str(exc_info.value).lower()

    def test_metadata_key_exceeds_char_limit(self):
        """Metadata key exceeding max_metadata_key_chars triggers MissionBoundaryViolation."""
        config = MissionBoundaryConfig(max_metadata_key_chars=64)
        defn = MissionDefinition(
            id=MissionId(value="M001"),
            name="Test",
            description="Test",
            metadata=(("x" * 65, "value"),)  # Key is 65 chars
        )
        with pytest.raises(MissionBoundaryViolation) as exc_info:
            validate_mission_definition(defn, config)

        assert "exceeds" in str(exc_info.value).lower() and "64" in str(exc_info.value)

    def test_metadata_value_exceeds_char_limit(self):
        """Metadata value exceeding max_metadata_value_chars triggers MissionBoundaryViolation."""
        config = MissionBoundaryConfig(max_metadata_value_chars=1000)
        defn = MissionDefinition(
            id=MissionId(value="M001"),
            name="Test",
            description="Test",
            metadata=(("key", "x" * 1001),)  # Value is 1001 chars
        )
        with pytest.raises(MissionBoundaryViolation) as exc_info:
            validate_mission_definition(defn, config)

        assert "exceeds" in str(exc_info.value).lower() and "1000" in str(exc_info.value)


class TestUnicodeAndSpecialCharacters:
    """Tests for unicode emoji and special characters in mission fields."""

    def test_unicode_emoji_in_name_within_limit(self):
        """Unicode emoji in name within char limit is allowed."""
        defn = MissionDefinition(
            id=MissionId(value="M001"),
            name="Test 🚀 Mission",  # Emoji within limit
            description="Test"
        )
        validate_mission_definition(defn)  # Should not raise

    def test_unicode_emoji_exceeding_char_limit(self):
        """Unicode emoji causing name to exceed char limit triggers violation."""
        config = MissionBoundaryConfig(max_name_chars=20)
        # Each emoji can be multiple bytes but counts as 1 char in Python
        defn = MissionDefinition(
            id=MissionId(value="M001"),
            name="x" * 18 + "🚀🚀",  # 20 chars total
            description="Test"
        )
        validate_mission_definition(defn, config)  # Should not raise (exactly 20)

        defn2 = MissionDefinition(
            id=MissionId(value="M001"),
            name="x" * 18 + "🚀🚀🚀",  # 21 chars total
            description="Test"
        )
        with pytest.raises(MissionBoundaryViolation):
            validate_mission_definition(defn2, config)

    def test_metadata_value_with_newlines(self):
        """Metadata value with newlines is allowed but counts in char limit."""
        defn = MissionDefinition(
            id=MissionId(value="M001"),
            name="Test",
            description="Test",
            metadata=(("key", "line1\nline2\nline3"),)
        )
        validate_mission_definition(defn)  # Should not raise
