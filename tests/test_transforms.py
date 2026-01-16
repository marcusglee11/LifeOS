"""Tests for Phase 3 transforms."""

import pytest
from typing import Any

# Import the package to trigger transform registration
from runtime.orchestration import transforms
from runtime.orchestration.transforms.base import execute_transform, get_transform


class TestTransformRegistry:
    """Tests for transform registry operations."""
    
    def test_transforms_registered(self):
        """All three transforms should be registered on import."""
        assert get_transform("to_build_packet") is not None
        assert get_transform("to_review_packet") is not None
        assert get_transform("to_council_context_pack") is not None
    
    def test_unknown_transform_raises_keyerror(self):
        """Unknown transform name should raise KeyError."""
        with pytest.raises(KeyError, match="TransformNotFound"):
            get_transform("nonexistent_transform")


class TestToBuildPacket:
    """Tests for to_build_packet transform."""
    
    def test_basic_transform(self):
        """Should produce BUILD_PACKET from design output."""
        packet = {
            "scope": {"area": "tests"},
            "deliverables": ["file1.py", "file2.py"],
            "constraints": ["no governance changes"],
        }
        result, evidence = execute_transform("to_build_packet", packet, {})
        
        assert result["packet_type"] == "BUILD_PACKET"
        assert result["phase"] == "build"
        assert result["build_ready"] is True
        assert evidence["transform"] == "to_build_packet"
        assert evidence["version"] == "1.0.0"
        assert "input_hash" in evidence
        assert "output_hash" in evidence
    
    def test_preserves_deliverables(self):
        """Should pass through deliverables list."""
        packet = {"deliverables": ["a.py", "b.py"]}
        result, _ = execute_transform("to_build_packet", packet, {})
        assert result["deliverables"] == ["a.py", "b.py"]


class TestToReviewPacket:
    """Tests for to_review_packet transform."""
    
    def test_basic_transform(self):
        """Should produce REVIEW_PACKET from build output."""
        packet = {
            "outcome": "success",
            "artifacts": ["file.py"],
            "summary": "Built successfully",
        }
        context = {
            "test_results": {"passed": 10, "failed": 0},
            "evidence": {"hash": "abc123"},
        }
        result, evidence = execute_transform("to_review_packet", packet, context)
        
        assert result["packet_type"] == "REVIEW_PACKET"
        assert result["phase"] == "review"
        assert result["outcome"] == "success"
        assert result["test_results"]["passed"] == 10
        assert evidence["transform"] == "to_review_packet"


class TestToCouncilContextPack:
    """Tests for to_council_context_pack transform."""
    
    def test_from_build_packet(self):
        """Should produce COUNCIL_CONTEXT_PACK from BUILD_PACKET."""
        packet = {
            "packet_type": "BUILD_PACKET",
            "scope": {"summary": "Build tests"},
        }
        result, evidence = execute_transform("to_council_context_pack", packet, {})
        
        assert result["packet_type"] == "COUNCIL_CONTEXT_PACK"
        assert result["review_type"] == "build_review"
        assert result["phase"] == "council"
        assert evidence["transform"] == "to_council_context_pack"
    
    def test_from_review_packet(self):
        """Should identify review_type correctly for REVIEW_PACKET."""
        packet = {
            "packet_type": "REVIEW_PACKET",
            "summary": "Completed",
        }
        result, _ = execute_transform("to_council_context_pack", packet, {})
        
        assert result["review_type"] == "completion_review"


class TestNegativeCases:
    """Negative tests: transform rejection cases."""
    
    def test_reject_unknown_transform(self):
        """NEGATIVE: Unknown transform name should be rejected."""
        with pytest.raises(KeyError, match="TransformNotFound"):
            execute_transform("invalid_transform_name", {}, {})
    
    def test_reject_none_packet(self):
        """NEGATIVE: None packet should raise TypeError."""
        with pytest.raises((TypeError, AttributeError)):
            execute_transform("to_build_packet", None, {})  # type: ignore
    
    def test_reject_non_dict_packet(self):
        """NEGATIVE: Non-dict packet should raise TypeError."""
        bad_input: Any = "not-a-dict"
        with pytest.raises((TypeError, AttributeError)):
            execute_transform("to_build_packet", bad_input, {})
